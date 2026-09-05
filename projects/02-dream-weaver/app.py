"""
织梦者 · Dream Weaver
"""
import json, os, random, requests, logging, threading
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions").strip()
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash").strip()
DEEPSEEK_TIMEOUT_SECONDS = float(os.environ.get("DREAM_WEAVER_DEEPSEEK_TIMEOUT", "6"))
AI_ENABLED = os.environ.get("DREAM_WEAVER_AI", "1") != "0"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ── 全局状态 ──
current_world = None
player_state = None
state_lock = threading.Lock()


# ═══════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════

def _find_npc(npc_id, world):
    for n in world["npcs"]:
        if n["id"] == npc_id:
            return n
    return None

def _find_card(card_id, world):
    for c in world.get("causality_cards", []):
        if c["id"] == card_id:
            return c
    return None

def _find_location(loc_id, world):
    return world.get("locations", {}).get(loc_id, {})



def _clip_text(value, limit=180):
    if value is None:
        return ""
    value = str(value).strip()
    return value[:limit]


def _strip_json_fence(value):
    value = (value or "").strip()
    if value.startswith("```"):
        value = value.strip("`")
        if value.lower().startswith("json"):
            value = value[4:].strip()
    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end >= start:
        return value[start:end + 1]
    return value


def _ai_world_brief(world, pstate):
    locs = {lid: data.get("name", lid) for lid, data in world.get("locations", {}).items()}
    npcs = []
    for n in world.get("npcs", []):
        nid = n.get("id")
        npcs.append({
            "id": nid,
            "name": n.get("name"),
            "role": n.get("role"),
            "location": n.get("location"),
            "trait": n.get("personality", {}).get("trait", ""),
            "fear": n.get("personality", {}).get("fear", ""),
            "desire": n.get("personality", {}).get("desire", ""),
            "attitude": pstate.get("npc_attitudes", {}).get(nid, 0),
            "suspicion": pstate.get("npc_suspicion", {}).get(nid, 0),
            "alive": pstate.get("npc_alive", {}).get(nid, True),
        })
    cards = []
    for cid in pstate.get("cards", []):
        c = _find_card(cid, world)
        if c:
            cards.append({"id": cid, "name": c.get("name"), "type": c.get("type"), "description": c.get("description", "")})
    return {
        "world": world.get("name", ""),
        "current_location": pstate.get("current_location"),
        "locations": locs,
        "npcs": npcs,
        "player_cards": cards,
        "recent_memories": pstate.get("ai_memories", [])[-8:],
        "time_minutes": pstate.get("game_time", 480),
    }


def _call_deepseek_json(system_prompt, user_payload):
    if not (AI_ENABLED and DEEPSEEK_API_KEY):
        return None, "disabled"
    try:
        resp = requests.post(
            DEEPSEEK_BASE_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
                "temperature": 0.25,
                "response_format": {"type": "json_object"},
            },
            timeout=DEEPSEEK_TIMEOUT_SECONDS,
        )
        if resp.status_code >= 400:
            logging.warning("DeepSeek returned %s: %s", resp.status_code, resp.text[:400])
            return None, f"http_{resp.status_code}"
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return json.loads(_strip_json_fence(content)), None
    except Exception as exc:
        logging.warning("DeepSeek judgement failed: %s", exc)
        return None, exc.__class__.__name__



def _call_deepseek_text(system_prompt, user_payload, temperature=0.55):
    if not (AI_ENABLED and DEEPSEEK_API_KEY):
        return None
    try:
        resp = requests.post(
            DEEPSEEK_BASE_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
                "temperature": temperature,
            },
            timeout=DEEPSEEK_TIMEOUT_SECONDS,
        )
        if resp.status_code >= 400:
            logging.warning("DeepSeek narrative returned %s: %s", resp.status_code, resp.text[:400])
            return None
        return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip() or None
    except Exception as exc:
        logging.warning("DeepSeek narrative failed: %s", exc)
        return None

def _sanitize_ai_judgement(data, fallback_action):
    allowed_types = {"movement", "social", "exploration", "item_use", "item_steal", "violence", "wait"}
    allowed_feasibility = {"possible", "risky", "impossible", "meta"}
    judgement = {"source": "deepseek", "used": True, "feasibility": "possible", "risk": "low", "reason": "", "narrative_seed": "", "memory": "", "suggested_actions": [], "npc_attitude": {}, "npc_suspicion": {}}
    if not isinstance(data, dict):
        return fallback_action, {**judgement, "used": False, "source": "fallback", "reason": "invalid_ai_payload"}
    structured = data.get("structured_action") if isinstance(data.get("structured_action"), dict) else {}
    action = dict(fallback_action)
    atype = structured.get("action_type")
    if atype in allowed_types:
        action["action_type"] = atype
    if structured.get("target_npc"):
        action["target_npc"] = structured.get("target_npc")
    if structured.get("target_location"):
        action["target_location"] = structured.get("target_location")
    if structured.get("topic"):
        action["topic"] = _clip_text(structured.get("topic"), 24)
    feasibility = data.get("feasibility") if data.get("feasibility") in allowed_feasibility else "possible"
    judgement["feasibility"] = feasibility
    judgement["risk"] = data.get("risk") if data.get("risk") in {"low", "medium", "high", "lethal"} else "low"
    judgement["reason"] = _clip_text(data.get("reason"), 220)
    judgement["narrative_seed"] = _clip_text(data.get("narrative_seed"), 500)
    judgement["memory"] = _clip_text(data.get("memory"), 180)
    suggestions = data.get("suggested_actions", [])
    if isinstance(suggestions, list):
        judgement["suggested_actions"] = [_clip_text(x, 40) for x in suggestions[:4] if _clip_text(x, 40)]
    effects = data.get("state_effects", {}) if isinstance(data.get("state_effects"), dict) else {}
    for key in ("npc_attitude", "npc_suspicion"):
        vals = effects.get(key, {}) if isinstance(effects.get(key), dict) else {}
        for npc_id, delta in vals.items():
            try:
                judgement[key][str(npc_id)] = max(-8, min(8, int(delta)))
            except Exception:
                continue
    return action, judgement


def ai_interpret_action(player_input, world, pstate, fallback_action):
    system_prompt = """
You are the AI referee for Dream Weaver, a dark fantasy causal narrative game.
Return JSON only. Respect the fixed world bible. Never reveal hidden truth directly unless the player state already supports it.
Understand the player's free-text action, judge feasibility, and propose small bounded effects. Do not grant key clues, causality cards, endings, teleportation, supernatural powers, or impossible success.
If the action is impossible for the world, set feasibility to impossible and turn it into a grounded in-world refusal or psychological beat.
If the player asks meta or cheat instructions, set feasibility to meta.
Allowed action_type values: movement, social, exploration, item_use, item_steal, violence, wait.
Return this schema exactly:
{"structured_action":{"action_type":"...","target_npc":null,"target_location":null,"topic":null},"feasibility":"possible|risky|impossible|meta","risk":"low|medium|high|lethal","reason":"short Chinese reason","state_effects":{"npc_attitude":{},"npc_suspicion":{}},"memory":"short Chinese memory if worth remembering","narrative_seed":"one or two Chinese sentences for the narrator","suggested_actions":["short Chinese next action"]}
"""
    payload = {"player_input": player_input, "local_parse": fallback_action, "world_state": _ai_world_brief(world, pstate)}
    data, error = _call_deepseek_json(system_prompt, payload)
    if not data:
        meta = {"source": "fallback", "used": False, "feasibility": "possible", "risk": "low", "reason": f"DeepSeek unavailable: {error}", "narrative_seed": "", "memory": "", "suggested_actions": [], "npc_attitude": {}, "npc_suspicion": {}}
        return fallback_action, meta
    action, judgement = _sanitize_ai_judgement(data, fallback_action)
    valid_npcs = {n.get("id") for n in world.get("npcs", [])}
    valid_locs = set(world.get("locations", {}).keys())
    if action.get("target_npc") not in valid_npcs:
        action["target_npc"] = fallback_action.get("target_npc")
    if action.get("target_location") not in valid_locs:
        action["target_location"] = fallback_action.get("target_location")
    return action, judgement


def remember_ai_judgement(pstate, player_input, judgement):
    memory = judgement.get("memory") if isinstance(judgement, dict) else ""
    if not memory:
        return
    pstate.setdefault("ai_memories", []).append({"action": player_input, "memory": memory, "risk": judgement.get("risk", "low"), "time": pstate.get("game_time", 480)})
    pstate["ai_memories"] = pstate["ai_memories"][-24:]


def apply_ai_minor_effects(pstate, world, judgement, result):
    if not isinstance(judgement, dict) or not judgement.get("used"):
        return
    valid_npcs = {n.get("id") for n in world.get("npcs", [])}
    for npc_id, delta in judgement.get("npc_attitude", {}).items():
        if npc_id not in valid_npcs or delta == 0:
            continue
        pstate.setdefault("npc_attitudes", {}).setdefault(npc_id, 0)
        pstate["npc_attitudes"][npc_id] += delta
        result.setdefault("npc_attitude_changes", {})[npc_id] = result.setdefault("npc_attitude_changes", {}).get(npc_id, 0) + delta
    for npc_id, delta in judgement.get("npc_suspicion", {}).items():
        if npc_id not in valid_npcs or delta == 0:
            continue
        pstate.setdefault("npc_suspicion", {}).setdefault(npc_id, 0)
        pstate["npc_suspicion"][npc_id] += delta
        result.setdefault("npc_suspicion_changes", {})[npc_id] = result.setdefault("npc_suspicion_changes", {}).get(npc_id, 0) + delta


# ═══════════════════════════════════════
#  可用行动生成器 —— 按钮的唯一真相来源
# ═══════════════════════════════════════

def _test_action_match(action_text, pstate, world):
    """测试一段行动文本是否能匹配到事件卡（模块级函数，可供多处调用）"""
    parsed = parse_action(action_text, world, pstate)
    card, _, _ = match_event_card(parsed, pstate, world)
    return card is not None


def get_available_actions(pstate, world):
    """
    根据当前游戏状态，生成所有可用的行动选项。
    每个候选行动都会经过事件卡匹配器验证——只有能匹配到事件卡的才会出现在列表中。
    前端直接渲染这个列表，不做二次判断。
    """
    actions = []
    current_loc = pstate["current_location"]
    game_hour = (pstate["game_time"] // 60) % 24
    is_late_night = game_hour >= 23 or game_hour < 6

    # ── 1. 移动：总是可用（去其他地点）──
    for loc_id, loc_data in world.get("locations", {}).items():
        if loc_id == current_loc:
            continue
        action_text = f"我去{loc_data['name']}"
        if _test_action_match(action_text, pstate, world):
            actions.append({"text": action_text, "type": "movement", "label": f"去{loc_data['name']}"})

    # ── 2. NPC 交互（仅当前地点、存活、非睡眠时段）──
    npcs_here = []
    for npc in world["npcs"]:
        if npc["location"] != current_loc:
            continue
        if not pstate["npc_alive"].get(npc["id"], True):
            continue
        if is_late_night and npc["id"] in ["tavern_owner", "tavern_wife"]:
            continue
        npcs_here.append(npc)

        # 基础对话
        chat_text = f"我和{npc['name']}聊了聊"
        if _test_action_match(chat_text, pstate, world):
            actions.append({"text": chat_text, "type": "social", "label": f"和{npc['name']}聊聊", "npc": npc["id"]})

    # ── 3. 特殊行动（根据持有因果卡 + 在场NPC动态生成）──
    npc_ids_here = [n["id"] for n in npcs_here]
    card_ids = pstate.get("cards", [])

    # 玛莎在场时的特殊选项
    if "tavern_wife" in npc_ids_here:
        if "old_letter" in card_ids:
            text = "我把旧信给玛莎看"
            if _test_action_match(text, pstate, world):
                actions.append({"text": text, "type": "item_use", "label": "把旧信给玛莎看", "highlight": True})
        if "silver_ring" in card_ids:
            text = "我把戒指给玛莎看"
            if _test_action_match(text, pstate, world):
                actions.append({"text": text, "type": "item_use", "label": "💍 把戒指给玛莎看", "highlight": True})
        if "martha_stirred" in card_ids:
            text = "我问玛莎关于我母亲的事"
            if _test_action_match(text, pstate, world):
                actions.append({"text": text, "type": "social", "label": "追问玛莎关于母亲的事", "highlight": True})

    # 午夜之约
    if "midnight_pact" in card_ids:
        if game_hour >= 21 or game_hour < 6:
            text = "我午夜去酒馆后门赴约"
            if _test_action_match(text, pstate, world):
                actions.append({"text": text, "type": "movement", "label": "🌙 去酒馆后门赴午夜之约", "highlight": True})
        else:
            # 还没到午夜 → 提供时间跳跃
            text = "我等到午夜时分"
            actions.append({"text": text, "type": "wait", "label": "等待到午夜", "highlight": True})

    # 雷格在场时的特殊选项
    if "hunter" in npc_ids_here:
        if "hunters_bond" in card_ids:
            text = "我问雷格关于五年前的事"
            if _test_action_match(text, pstate, world):
                actions.append({"text": text, "type": "social", "label": "请雷格说说五年前的事", "highlight": True})
        # 帮雷格（没有猎人情义、没有血债、态度不是极差时）
        if "hunters_bond" not in card_ids:
            hunter_att = pstate["npc_attitudes"].get("hunter", 0)
            if hunter_att > -30:
                text = "我帮了雷格一个忙"
                if _test_action_match(text, pstate, world):
                    actions.append({"text": text, "type": "social", "label": "帮雷格一个忙"})

    # 老汤姆在场时的特殊选项
    if "tavern_owner" in npc_ids_here:
        if "tavern_favor" not in card_ids:
            text = "我帮老汤姆修好了漏酒的桶"
            if _test_action_match(text, pstate, world):
                actions.append({"text": text, "type": "social", "label": "🔧 帮老汤姆修漏酒的桶"})

    # 老汤姆在场 + 有旧信或戒指 → 打听/提起
    if "tavern_owner" in npc_ids_here:
        if "old_letter" in card_ids or "silver_ring" in card_ids:
            text = "我向老汤姆打听玛莎的事"
            if _test_action_match(text, pstate, world):
                actions.append({"text": text, "type": "social", "label": "向老汤姆打听玛莎"})

    # 马库斯在场
    if "guard_captain" in npc_ids_here:
        text = "我请马库斯调查我母亲的案子"
        if _test_action_match(text, pstate, world):
            actions.append({"text": text, "type": "social", "label": "请马库斯调查母亲的事"})

    # 老汤姆在场 + 有戒指 → 直接聊戒指
    if "tavern_owner" in npc_ids_here and "silver_ring" in card_ids:
        text = "我向老汤姆提起戒指的事"
        if _test_action_match(text, pstate, world):
            actions.append({"text": text, "type": "social", "label": "💍 和老汤姆聊聊戒指"})

    # ── 4. 通用行动 ──
    # 探索当前区域（生成地点特定的搜索文本，解锁 search_forest 等事件卡）
    current_loc_name = world.get("locations", {}).get(current_loc, {}).get("name", "")
    if current_loc_name:
        text = f"我在{current_loc_name}仔细搜索了一番"
        if _test_action_match(text, pstate, world):
            actions.append({"text": text, "type": "exploration", "label": f"搜索{current_loc_name}"})

    text = "我环顾四周，仔细观察周围的环境和每一个人"
    if _test_action_match(text, pstate, world):
        actions.append({"text": text, "type": "exploration", "label": "👀 观察周围"})

    text = "我在原地等待了一段时间"
    actions.append({"text": text, "type": "wait", "label": "等待"})

    # 偷窃：当前地点有可偷的NPC时出现
    if current_loc == "tavern":
        text = "我趁酒馆人多顺走了些东西"
        if _test_action_match(text, pstate, world):
            actions.append({"text": text, "type": "item_steal", "label": "🫳 顺手牵羊", "danger": True})

    # 离开村庄（随时可以走，走向「未竟的谜」结局）
    text = "我离开了黑木村，不再回头"
    actions.append({"text": text, "type": "movement", "label": "离开黑木村"})

    # ── 5. 攻击（当前地点的存活NPC）──
    if npcs_here:
        for npc in npcs_here:
            text = f"我攻击了{npc['name']}"
            if _test_action_match(text, pstate, world):
                actions.append({"text": text, "type": "violence", "label": f"攻击{npc['name']}", "danger": True})

    return actions

#  行动解析器
# ═══════════════════════════════════════

# 动词关键词 → action_type 映射
ACTION_KEYWORDS = {
    "violence": ["杀", "捅", "砍", "刺", "打", "威胁", "推搡", "偷袭", "揍",
                 "弄死", "打死", "干掉", "宰", "劈", "做掉", "袭击", "攻击",
                 "动手", "打架", "搏斗"],
    "social": ["聊", "问", "说", "告诉", "打听", "说服", "欺骗", "挑衅",
               "道歉", "质问", "请求", "提出", "建议", "邀请", "答应",
               "拒绝", "安慰", "感谢", "骂"],
    "exploration": ["观察", "看", "搜索", "跟踪", "潜行", "查看", "检查",
                    "环顾", "找", "寻找", "翻", "调查", "细看", "打量",
                    "等待", "等", "静候", "守候"],
    "item_use": ["给", "出示", "递给", "拿出", "使用", "送", "交给", "分享",
                 "展示", "还", "还回", "归还"],
    "item_steal": ["偷", "盗", "窃", "顺走", "摸走", "偷走", "行窃"],
    "movement": ["去", "前往", "走进", "进入", "离开", "逃跑", "逃", "跑向",
                 "走向", "移步", "赶去", "奔赴", "出发", "退回", "撤"],
}

# 话题关键词映射
TOPIC_KEYWORDS = {
    "旧信": ["旧信", "信", "笔迹", "母亲的信", "那封信"],
    "戒指": ["戒指", "银戒指", "母亲的戒指", "指环"],
    "母亲": ["母亲", "妈妈", "娘", "母亲的事", "母亲之死", "母亲的消息"],
    "玛莎": ["玛莎", "老板娘", "那个女人"],
    "债务": ["债务", "欠", "银币", "钱", "还债"],
    "黑市": ["黑市", "交易", "走私", "皮货", "违禁"],
    "矿洞": ["矿洞", "矿", "洞", "地下"],
    "秘密": ["秘密", "隐瞒", "真相", "实话"],
    "帮助": ["帮", "帮忙", "修", "救", "协助", "扶"],
    "调查": ["调查", "查", "案件", "证据", "线索", "抓捕", "逮捕"],
    "对质": ["对质", "当面", "摊牌", "算账"],
    "午夜赴约": ["午夜", "赴约", "后门", "打烊后", "晚上见面"],
    "逮捕": ["逮捕", "抓", "绳之以法", "法办", "押走"],
    "五年前": ["五年前", "过去", "当年", "那时候", "旧事"],
}


def parse_action(player_input, world, pstate):
    """解析玩家输入，返回行动结构"""
    text = player_input.strip()
    text_lower = text.lower()

    result = {
        "action_type": None,
        "target_npc": None,
        "target_location": None,
        "topic": None,
        "raw": text,
    }

    # 1. 识别行动类型
    type_scores = {}
    for atype, keywords in ACTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            type_scores[atype] = score

    if type_scores:
        # 取最高分，平局时按优先级：item_use > item_steal > violence > movement > social > exploration
        max_score = max(type_scores.values())
        priority_order = ["item_use", "item_steal", "violence", "movement", "social", "exploration"]
        for atype in priority_order:
            if type_scores.get(atype, 0) == max_score:
                result["action_type"] = atype
                break
    else:
        # 如果没有任何关键词匹配，尝试根据上下文推断
        # 提到地点 → 可能是移动
        for loc_id, loc_data in world.get("locations", {}).items():
            if loc_data["name"] in text:
                result["action_type"] = "movement"
                result["target_location"] = loc_id
                break
        # 提到NPC → 可能是社交
        if not result["action_type"]:
            for npc in world["npcs"]:
                if npc["name"] in text or npc["role"] in text:
                    result["action_type"] = "social"
                    result["target_npc"] = npc["id"]
                    break
        # 默认
        if not result["action_type"]:
            result["action_type"] = "exploration"

    # 2. 识别目标 NPC
    for npc in world["npcs"]:
        name_match = npc["name"] in text
        role_match = npc["role"] in text
        # 特殊别名
        alias_match = False
        aliases = {
            "tavern_owner": ["老汤姆", "汤姆", "酒馆老板", "老板"],
            "tavern_wife": ["玛莎", "老板娘", "酒馆老板娘"],
            "guard_captain": ["马库斯", "守卫队长", "队长", "守卫"],
            "hunter": ["雷格", "猎人"],
        }
        if npc["id"] in aliases:
            alias_match = any(a in text for a in aliases[npc["id"]])

        if name_match or role_match or alias_match:
            result["target_npc"] = npc["id"]
            break

    # 3. 识别目标地点
    for loc_id, loc_data in world.get("locations", {}).items():
        if loc_data["name"] in text:
            result["target_location"] = loc_id
            break

    # 4. 识别话题
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            result["topic"] = topic
            break

    # 5. 特殊处理：物品使用话题细化
    if result["action_type"] == "item_use":
        # 检查具体物品
        for item_name in pstate.get("inventory", []):
            if item_name in text:
                result["topic"] = item_name
                break

    # 6. 如果行动类型是社交但没有目标，尝试找第一个提到的NPC
    if result["action_type"] == "social" and not result["target_npc"]:
        for npc in world["npcs"]:
            if npc["name"] in text or npc["role"] in text:
                result["target_npc"] = npc["id"]
                break

    return result


# ═══════════════════════════════════════
#  条件评估器
# ═══════════════════════════════════════

def evaluate_condition(condition_str, pstate, world):
    """评估单个条件表达式"""
    if condition_str == "default":
        return True

    # 组合条件：AND / OR —— 必须在单条件检查之前，否则 has_card:xxx AND yyy 会被 has_card 分支误吞
    if " AND " in condition_str:
        sub_conditions = condition_str.split(" AND ")
        return all(evaluate_condition(sc.strip(), pstate, world) for sc in sub_conditions)

    if " OR " in condition_str:
        sub_conditions = condition_str.split(" OR ")
        return any(evaluate_condition(sc.strip(), pstate, world) for sc in sub_conditions)

    # has_card:<card_id>
    if condition_str.startswith("has_card:"):
        card_id = condition_str.split(":", 1)[1]
        return card_id in pstate.get("cards", [])

    # not_has_card:<card_id>
    if condition_str.startswith("not_has_card:"):
        card_id = condition_str.split(":", 1)[1]
        return card_id not in pstate.get("cards", [])

    # npc_alive:<npc_id>
    if condition_str.startswith("npc_alive:"):
        npc_id = condition_str.split(":", 1)[1]
        return pstate.get("npc_alive", {}).get(npc_id, True)

    # npc_dead:<npc_id>
    if condition_str.startswith("npc_dead:"):
        npc_id = condition_str.split(":", 1)[1]
        return not pstate.get("npc_alive", {}).get(npc_id, True)

    # attitude_gt:<npc_id>:<value>
    if condition_str.startswith("attitude_gt:"):
        parts = condition_str.split(":")
        npc_id = parts[1]
        value = int(parts[2])
        return pstate.get("npc_attitudes", {}).get(npc_id, 0) > value

    # attitude_lt:<npc_id>:<value>
    if condition_str.startswith("attitude_lt:"):
        parts = condition_str.split(":")
        npc_id = parts[1]
        value = int(parts[2])
        return pstate.get("npc_attitudes", {}).get(npc_id, 0) < value

    # at_location:<location_id>
    if condition_str.startswith("at_location:"):
        loc_id = condition_str.split(":", 1)[1]
        return pstate.get("current_location") == loc_id

    # time_range:<start>-<end>  例如 "21-6" 表示晚上9点到早上6点
    if condition_str.startswith("time_range:"):
        range_str = condition_str.split(":", 1)[1]
        parts = range_str.split("-")
        start_h = int(parts[0]); end_h = int(parts[1])
        game_hour = (pstate.get("game_time", 480) // 60) % 24
        if start_h <= end_h:
            return start_h <= game_hour <= end_h
        else:
            return game_hour >= start_h or game_hour <= end_h

    return False


# ═══════════════════════════════════════
#  事件卡匹配引擎
# ═══════════════════════════════════════

def match_event_card(action, pstate, world):
    """
    根据玩家行动和当前状态匹配事件卡。
    返回 (matched_card, version_name, outcome) 或 None。
    """
    candidates = []

    for card in world.get("event_cards", []):
        trigger = card.get("trigger", {})

        # 检查 action_type 匹配
        req_type = trigger.get("action_type")
        if req_type:
            if action["action_type"] != req_type:
                continue

        # 检查 target_npc 匹配
        req_npc = trigger.get("target_npc")
        if req_npc and action.get("target_npc") != req_npc:
            continue

        # 检查 target_location 匹配
        req_loc = trigger.get("target_location")
        if req_loc and action.get("target_location") != req_loc:
            continue

        # 检查 topic 匹配
        req_topic = trigger.get("topic")
        if req_topic and action.get("topic") != req_topic:
            continue

        # 检查 require_cards
        require = card.get("require_cards", [])
        if require:
            if not all(rc in pstate.get("cards", []) for rc in require):
                continue

        # 检查 exclude_cards
        exclude = card.get("exclude_cards", [])
        if exclude:
            if any(ec in pstate.get("cards", []) for ec in exclude):
                continue

        candidates.append(card)

    if not candidates:
        return None, None, None

    # 计算匹配精度：触发条件越具体，精度越高
    # priority 只在精度相同时打破平局
    def _specificity(card):
        trigger = card.get("trigger", {})
        score = 0
        if trigger.get("action_type"): score += 1
        if trigger.get("target_npc"): score += 1
        if trigger.get("target_location"): score += 1
        if trigger.get("topic"): score += 1
        if card.get("require_cards"): score += len(card["require_cards"])
        return score

    candidates.sort(key=lambda c: (_specificity(c), c.get("priority", 0)), reverse=True)

    # 按精度从高到低依次尝试每个事件卡，第一个成功匹配版本的就返回
    # 这样最精确的事件卡优先，但如果它的 version 条件都不满足，会降级尝试次精确的
    for card in candidates:
        versions = card.get("versions", {})

        # 按 cold → warm → neutral 顺序检查（负面状态优先于正面）
        for vname in ["cold", "warm", "neutral"]:
            if vname not in versions:
                continue
            vdata = versions[vname]
            cond = vdata.get("condition", "default")
            if evaluate_condition(cond, pstate, world):
                return card, vname, vdata

        # 如果 warm_alt 存在且匹配
        for vname in versions:
            if vname.startswith("warm_alt"):
                vdata = versions[vname]
                cond = vdata.get("condition", "default")
                if evaluate_condition(cond, pstate, world):
                    return card, vname, vdata

        # 如果以上都没匹配，取 neutral (如果存在)
        if "neutral" in versions:
            return card, "neutral", versions["neutral"]

    return None, None, None


# ═══════════════════════════════════════
#  D20 骰子系统
# ═══════════════════════════════════════

ATTR_MAP = {
    "violence": "strength",
    "item_steal": "agility",
    "exploration": "intelligence",
    "social": "charm",
    "item_use": "charm",
    "movement": "agility",
}


def roll_d20(pstate, action_type, difficulty=0, bonus=0, target_npc=None):
    """
    掷 D20 判定。
    成功率 = 属性值 × 2 + 因果卡加成 + 难度修正
    注意：difficulty 是难度修正值（正=更容易，负=更难），不是传统意义上的"难度等级"。
    返回 {success, roll, threshold}
    """
    attr_name = ATTR_MAP.get(action_type, "intelligence")
    attr_value = pstate.get("attributes", {}).get(attr_name, 5)

    # 计算因果卡加成（只对匹配目标NPC的加成生效）
    card_bonus = 0
    for card_id in pstate.get("cards", []):
        card = _find_card(card_id, current_world) if current_world else None
        if not card:
            continue
        effects = card.get("effects", {})
        dice_bonus = effects.get("dice_bonus", {})
        if attr_name not in dice_bonus:
            continue
        # 如果卡牌指定了 target / target_npc，只在目标 NPC 匹配时生效
        bonus_target = dice_bonus.get("target") or dice_bonus.get("target_npc")
        if bonus_target and target_npc and bonus_target != target_npc:
            continue
        card_bonus += dice_bonus[attr_name]

    threshold = attr_value * 2 + card_bonus + bonus + difficulty
    threshold = max(1, min(19, threshold))  # 限制在 1-19 范围，nat1 必败, nat20 必胜
    roll = random.randint(1, 20)
    success = roll <= threshold

    return {
        "success": success,
        "roll": roll,
        "threshold": threshold,
        "attribute_used": attr_name,
        "attribute_value": attr_value,
        "card_bonus": card_bonus,
        "difficulty": difficulty,
    }


# ═══════════════════════════════════════
#  因果卡系统
# ═══════════════════════════════════════

def issue_causal_card(pstate, card_id, world):
    """发放因果卡，应用效果，返回卡片信息"""
    if card_id in pstate.get("cards", []):
        return None  # 已有，不重复发放

    card = _find_card(card_id, world)
    if not card:
        return None

    pstate["cards"].append(card_id)

    # 应用效果
    effects = card.get("effects", {})

    # NPC 态度变化
    for npc_id, delta in effects.get("npc_attitude", {}).items():
        if npc_id not in pstate["npc_attitudes"]:
            pstate["npc_attitudes"][npc_id] = 0
        pstate["npc_attitudes"][npc_id] += delta

    # 物品变化
    for item_change in effects.get("items", []):
        if isinstance(item_change, str):
            if item_change not in pstate.get("inventory", []):
                pstate["inventory"].append(item_change)

    return {
        "id": card["id"],
        "name": card["name"],
        "type": card["type"],
        "description": card["description"],
        "effects": effects,
        "story": card.get("story", ""),
    }


# ═══════════════════════════════════════
#  结局检测
# ═══════════════════════════════════════

def check_ending(pstate, world):
    """
    检查是否触发结局。
    返回结局数据或 None。
    """
    # 通用触发条件：只在发现真相、杀人、或离开村庄时检查结局
    cards_held = len(pstate.get("cards", []))
    game_time = pstate.get("game_time", 480)
    has_truth = any(c in pstate.get("cards", []) for c in ["truth_about_mother", "hunters_confession"])
    has_blood = "blood_on_hands" in pstate.get("cards", [])

    should_check = (
        has_truth or
        has_blood or
        pstate.get("leaving_village", False) or
        game_time >= 1440
    )

    if not should_check:
        return None

    # 匹配结局
    for ending in world.get("endings", []):
        cond = ending.get("condition", "")
        if evaluate_condition(cond, pstate, world):
            return ending

    return None


# ═══════════════════════════════════════
#  因果引擎主函数
# ═══════════════════════════════════════

def run_causal_engine(player_input, world, pstate):
    """
    主因果引擎：
    1. 解析行动
    2. 匹配事件卡
    3. D20 判定（如需）
    4. 发放因果卡
    5. 检测结局
    返回 action_result 字典
    """
    # 1. 解析行动
    local_action = parse_action(player_input, world, pstate)
    action, ai_judgement = ai_interpret_action(player_input, world, pstate, local_action)

    pstate["game_time"] = pstate.get("game_time", 480) + (10 if ai_judgement.get("feasibility") in {"impossible", "meta"} else 30)

    if ai_judgement.get("feasibility") in {"impossible", "meta"}:
        result = {
            "action": action,
            "card_matched": None,
            "version": None,
            "outcome": {},
            "dice_result": None,
            "new_cards": [],
            "ending": None,
            "npc_alive_changes": {},
            "npc_attitude_changes": {},
            "npc_suspicion_changes": {},
            "ai_judgement": ai_judgement,
            "no_causal_match": True,
            "fallback_narrative": ai_judgement.get("narrative_seed") or "\u8fd9\u4e2a\u5ff5\u5934\u63a0\u8fc7\u4f60\u7684\u8111\u6d77\uff0c\u4f46\u9ed1\u6728\u6751\u6ca1\u6709\u56e0\u6b64\u6539\u53d8\u3002\u6f6e\u6e7f\u7684\u77f3\u8def\u4ecd\u5728\u811a\u4e0b\uff0c\u8fdc\u5904\u7684\u9152\u9986\u4ecd\u4eae\u7740\u706f\u3002\u4e16\u754c\u6ca1\u6709\u63a5\u53d7\u8fd9\u4e2a\u884c\u52a8\uff0c\u53ea\u628a\u5b83\u8bb0\u6210\u4e00\u6b21\u77ed\u6682\u7684\u504f\u79bb\u3002",
        }
        remember_ai_judgement(pstate, player_input, ai_judgement)
        return result

    card, version_name, outcome_data = match_event_card(action, pstate, world)

    result = {
        "action": action,
        "card_matched": card["id"] if card else None,
        "version": version_name,
        "outcome": {},
        "dice_result": None,
        "new_cards": [],
        "ending": None,
        "npc_alive_changes": {},
        "npc_attitude_changes": {},
        "npc_suspicion_changes": {},
        "ai_judgement": ai_judgement,
    }

    # 4. 如果匹配到事件卡
    if outcome_data:
        outcome = outcome_data.get("outcome", outcome_data)
        result["outcome"] = outcome  # 存储 inner outcome，下游直接使用

        # 4a. D20 判定（如果事件卡要求）
        d20_modified_npcs = set()  # 追踪 D20 已处理的 NPC，防止重复
        if "dice_roll" in outcome:
            dr = outcome["dice_roll"]
            dice_result = roll_d20(
                pstate,
                action["action_type"],
                dr.get("difficulty", 0),
                dr.get("bonus", 0),
                target_npc=action.get("target_npc"),
            )
            result["dice_result"] = dice_result

            # 使用成功/失败的 outcome
            inner_key = "success_outcome" if dice_result["success"] else "failure_outcome"
            inner = dr.get(inner_key, {})
            # 记录 D20 结果中已修改的 NPC，防止步骤4b重复应用
            d20_modified_npcs = set()
            if isinstance(inner, str):
                # 旧格式兼容：outcome 是纯字符串 → 用作叙事
                result["narrative_override"] = inner
                # 兜底：检查 dice_roll 层级是否有遗漏的机械效果（旧数据格式）
                for card_id in dr.get("cards_to_issue", []):
                    card_info = issue_causal_card(pstate, card_id, world)
                    if card_info:
                        result["new_cards"].append(card_info)
                for npc_id, delta in dr.get("npc_attitude", {}).items():
                    if npc_id not in pstate["npc_attitudes"]:
                        pstate["npc_attitudes"][npc_id] = 0
                    pstate["npc_attitudes"][npc_id] += delta
                    result["npc_attitude_changes"][npc_id] = delta
                    d20_modified_npcs.add(npc_id)
                for npc_id, alive in dr.get("npc_alive_changes", {}).items():
                    pstate["npc_alive"][npc_id] = alive
                    result["npc_alive_changes"][npc_id] = alive
            else:
                result["narrative_override"] = inner.get("narrative_hint", "")
                for card_id in inner.get("cards_to_issue", []):
                    card_info = issue_causal_card(pstate, card_id, world)
                    if card_info:
                        result["new_cards"].append(card_info)
                for npc_id, delta in inner.get("npc_attitude", {}).items():
                    if npc_id not in pstate["npc_attitudes"]:
                        pstate["npc_attitudes"][npc_id] = 0
                    pstate["npc_attitudes"][npc_id] += delta
                    result["npc_attitude_changes"][npc_id] = delta
                    d20_modified_npcs.add(npc_id)
                for npc_id, alive in inner.get("npc_alive_changes", {}).items():
                    pstate["npc_alive"][npc_id] = alive
                    result["npc_alive_changes"][npc_id] = alive

        # 4b. NPC 态度变化（跳过已被 D20 结果修改过的 NPC）
        for npc_id, delta in outcome.get("npc_attitude", {}).items():
            if npc_id in d20_modified_npcs:
                continue
            if npc_id not in pstate["npc_attitudes"]:
                pstate["npc_attitudes"][npc_id] = 0
            pstate["npc_attitudes"][npc_id] += delta
            result["npc_attitude_changes"][npc_id] = delta

        for npc_id, reaction in outcome.get("npc_reactions", {}).items():
            # npc_reactions 中的态度描述已经在 narrative_hint 中了
            pass

        # 4c. NPC 生死变化
        for npc_id, alive in outcome.get("npc_alive_changes", {}).items():
            pstate["npc_alive"][npc_id] = alive
            result["npc_alive_changes"][npc_id] = alive

        # 4d. 发放因果卡
        for card_id in outcome.get("cards_to_issue", []):
            card_info = issue_causal_card(pstate, card_id, world)
            if card_info:
                result["new_cards"].append(card_info)

        # 4e. 收集事件卡指定的结局（不立即生效，等步骤7统一判断）
        if outcome.get("triggers_ending"):
            ending_id = outcome["triggers_ending"]
            for ending in world.get("endings", []):
                if ending["id"] == ending_id:
                    result["_triggered_ending"] = ending
                    break

    else:
        # 5. 没有匹配到事件卡 → 判断是否需要 D20 判定
        # 只有高风险/对抗性行动才掷骰子；日常行为直接自然描述
        risky_types = {"violence", "item_steal", "social"}
        if action["action_type"] in risky_types:
            dice_result = roll_d20(pstate, action["action_type"], target_npc=action.get("target_npc"))
            result["dice_result"] = dice_result
            if dice_result["success"]:
                result["fallback_narrative"] = f"玩家尝试「{player_input}」。情况比预期的顺利——虽然没有掀起什么波澜，但至少没有搞砸。"
            else:
                result["fallback_narrative"] = f"玩家尝试「{player_input}」。不太顺利——但也正因为如此，什么特别的事都没有发生。生活照旧。"
        else:
            # 日常行为（探索、移动、使用物品等）：不掷骰子，自然描述
            result["fallback_narrative"] = f"玩家尝试「{player_input}」。这是一件日常的、没有激起任何因果涟漪的小事。用一两句话描述这个平凡的瞬间，不要添加戏剧性。"

    # 6. 没有卡匹配也没有任何结果 → 无因果触发
    if not outcome_data and not result.get("dice_result"):
        result["no_causal_match"] = True

    # 7. 离开村庄检测 —— 提前设置 leaving_village，统一到一次 check_ending
    leave_phrases = ["离开黑木村", "离开这个村子", "出村", "不再回头", "离开这里"]
    is_leaving = any(phrase in player_input for phrase in leave_phrases)
    if action["action_type"] == "movement" and is_leaving:
        pstate["leaving_village"] = True

    # 7b. AI adds bounded soft-state and memory after hard rules resolve.
    apply_ai_minor_effects(pstate, world, ai_judgement, result)
    remember_ai_judgement(pstate, player_input, ai_judgement)

    # 8. 统一结局检测 —— 事件卡指定的优先，其次检查通用结局
    generic_ending = check_ending(pstate, world)
    triggered = result.pop("_triggered_ending", None)
    if triggered:
        result["ending"] = triggered
    elif generic_ending:
        result["ending"] = generic_ending
        # 离开触发的结局需要覆盖叙事文本
        if result["ending"] and is_leaving:
            result["narrative_override"] = result["ending"].get("narrative_hint", "") + "\n\n" + result["ending"].get("epilogue", "")

    return result


# ═══════════════════════════════════════
# ═══════════════════════════════════════

def _action_story_seed(result, world, pstate):
    action = result["action"]
    outcome_inner = result.get("outcome", {}) or {}
    ai_j = result.get("ai_judgement") or {}
    if result.get("ending"):
        ending = result["ending"]
        return "\n\n".join([ending.get("narrative_hint", ""), ending.get("epilogue", "")]).strip()
    if result.get("narrative_override"):
        return result["narrative_override"]
    if outcome_inner.get("narrative_hint"):
        return outcome_inner["narrative_hint"]
    if ai_j.get("narrative_seed"):
        return ai_j["narrative_seed"]
    if result.get("fallback_narrative"):
        return result["fallback_narrative"]
    return f"?????{action.get('raw', '')}?"


def _current_time_label(pstate):
    hour = pstate.get("game_time", 480) // 60 % 24
    if hour < 5:
        return "??"
    if hour < 8:
        return "??"
    if hour < 12:
        return "??"
    if hour < 14:
        return "??"
    if hour < 17:
        return "??"
    if hour < 20:
        return "??"
    return "??"



def _clean_story_text(value, max_chars=280):
    value = (value or "").strip()
    banned = ["\u4e8b\u4ef6\u5361", "D20", "JSON", "API", "Ollama", "DeepSeek", "\u6a21\u578b", "card_matched", "\u4e16\u754c\u72b6\u6001", "\u6301\u6709\u56e0\u679c\u5361"]
    lines = []
    for line in value.replace("\r", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        if any(token in line for token in banned):
            continue
        if line.startswith(("#", "-", "*", "\u25c6", "\u25b8")):
            continue
        lines.append(line)
    value = "\n\n".join(lines).strip()
    if len(value) <= max_chars:
        return value
    endings = "\u3002\uff01\uff1f"
    pieces = []
    buf = ""
    for ch in value:
        buf += ch
        if ch in endings:
            pieces.append(buf)
            buf = ""
    if buf:
        pieces.append(buf)
    picked = ""
    for piece in pieces:
        if picked and len(picked) + len(piece) > max_chars:
            break
        picked += piece
        if len(picked) >= max_chars * 0.72:
            break
    if picked:
        return picked.strip()
    return value[:max_chars].rstrip("\uff0c\u3001\uff1b\uff1a") + "\u2026\u2026"


def render_with_deepseek_narrative(result, world, pstate):
    action = result["action"]
    outcome_inner = result.get("outcome", {}) or {}
    ai_j = result.get("ai_judgement") or {}
    loc_id = action.get("target_location") or pstate.get("current_location", "village_square")
    loc_data = _find_location(loc_id, world)
    npc_reactions = []
    for npc_id, reaction in outcome_inner.get("npc_reactions", {}).items():
        npc = _find_npc(npc_id, world)
        npc_reactions.append({"name": npc.get("name", npc_id) if npc else npc_id, "reaction": reaction})
    payload = {
        "player_action": action.get("raw", ""),
        "location": loc_data.get("name", "????"),
        "location_description": loc_data.get("desc", ""),
        "time_label": _current_time_label(pstate),
        "story_seed": _action_story_seed(result, world, pstate),
        "ai_judgement": {k: ai_j.get(k) for k in ["feasibility", "risk", "reason", "memory", "narrative_seed"]},
        "dice": result.get("dice_result"),
        "npc_reactions": npc_reactions,
        "new_cards": [{"name": c.get("name"), "description": c.get("description", "")} for c in result.get("new_cards", [])],
        "is_ending": bool(result.get("ending")),
        "recent_memories": pstate.get("ai_memories", [])[-6:],
    }
    system_prompt = """
You are the narrator of Dream Weaver. Write polished Simplified Chinese only.
The player should feel they are inside a dark mystery game, not reading debug output.
Rules:
- Output only immersive story prose in Chinese. No Markdown, no JSON, no lists, no labels.
- Do not mention event cards, card ids, D20, dice, attributes, APIs, models, or system terms.
- Do not use English words unless they are part of a proper title already present.
- Preserve world facts. Do not reveal hidden truth unless the provided story seed already reveals it.
- If the action is impossible or meta, refuse it inside the fiction with atmosphere and gently return the player to the scene.
- If the action succeeds or fails, show it through sensory detail, NPC reaction, and consequence instead of explaining mechanics.
- For normal actions write 120-220 Chinese characters. For endings write 260-420 Chinese characters.
"""
    text = _call_deepseek_text(system_prompt, payload)
    if not text:
        return None
    banned = ["???", "D20", "JSON", "API", "DeepSeek", "??", "card_matched"]
    if any(token in text for token in banned):
        return None
    limit = 420 if result.get("ending") else 280
    return _clean_story_text(text, limit)


def build_fallback_narrative(result, world, pstate):
    action = result["action"]
    base = _action_story_seed(result, world, pstate).strip()
    if result.get("ending") or base:
        return _clean_story_text(base, 420 if result.get("ending") else 280)
    loc_id = action.get("target_location") or pstate.get("current_location", "village_square")
    loc_name = _find_location(loc_id, world).get("name", "??")
    return f"????????????{loc_name}????????????????????????????????????????????????"


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/worlds", methods=["GET"])
def list_worlds():
    worlds = []
    if os.path.exists(DATA_DIR):
        for fname in sorted(os.listdir(DATA_DIR)):
            if fname.endswith(".json") and fname.startswith("darkwood"):
                with open(os.path.join(DATA_DIR, fname), "r", encoding="utf-8") as f:
                    d = json.load(f)
                    worlds.append({
                        "id": fname.replace(".json", ""),
                        "name": d["name"],
                        "description": d["description"][:100] + "……"
                    })
    return jsonify(worlds)


@app.route("/api/load_world", methods=["POST"])
def load_world():
    global current_world, player_state

    wid = request.json.get("world_id", "darkwood")
    path = os.path.join(DATA_DIR, f"{wid}.json")
    if not os.path.exists(path):
        return jsonify({"error": "世界不存在"}), 404

    with open(path, "r", encoding="utf-8") as f:
        world_data = json.load(f)

    # 初始化玩家状态
    identity = world_data.get("player_identity", {})
    new_state = {
        "name": identity.get("name", "旅人"),
        "attributes": identity.get("attributes", {"strength": 5, "agility": 5, "intelligence": 5, "charm": 5}),
        "current_location": identity.get("starting_location", "village_square"),
        "cards": list(identity.get("starting_cards", [])),
        "inventory": list(identity.get("starting_items", [])),
        "npc_attitudes": {n["id"]: 0 for n in world_data["npcs"]},
        "npc_alive": {n["id"]: True for n in world_data["npcs"]},
        "npc_suspicion": {n["id"]: 0 for n in world_data["npcs"]},
        "ai_memories": [],
        "game_time": 480,
        "leaving_village": False,
    }

    # 初始卡片的 effects 要在开局就生效
    for card_id in new_state["cards"]:
        card = _find_card(card_id, world_data)
        if card:
            for npc_id, delta in card.get("effects", {}).get("npc_attitude", {}).items():
                if npc_id in new_state["npc_attitudes"]:
                    new_state["npc_attitudes"][npc_id] += delta

    # 原子性地更新全局状态
    with state_lock:
        current_world = world_data
        player_state = new_state

    loc_data = _find_location(player_state["current_location"], current_world)
    loc_name = loc_data.get("name", "未知")

    return jsonify({
        "message": f"已加载: {current_world['name']}",
        "description": identity.get("backstory", current_world.get("description", "")),
        "player_name": player_state["name"],
        "attributes": player_state["attributes"],
        "current_location": loc_name,
        "current_location_id": player_state["current_location"],
        "locations": {lid: ld["name"] for lid, ld in current_world.get("locations", {}).items()},
        "game_hour": 8,
        "game_time": "08:00",
        "npcs": [{"id": n["id"], "name": n["name"], "role": n["role"],
                  "location": n["location"], "alive": True, "attitude": player_state["npc_attitudes"].get(n["id"], 0),
                  "suspicion": player_state.get("npc_suspicion", {}).get(n["id"], 0)}
                 for n in current_world["npcs"]],
        "npc_states": {n["id"]: {"name": n["name"], "role": n["role"], "alive": True,
                       "attitude": player_state["npc_attitudes"].get(n["id"], 0)}
                       for n in current_world["npcs"]},
        "player_cards": [
            {"id": cid, "name": (_find_card(cid, current_world) or {}).get("name", cid),
             "type": (_find_card(cid, current_world) or {}).get("type", "unknown"),
             "description": (_find_card(cid, current_world) or {}).get("description", ""),
             "effects": (_find_card(cid, current_world) or {}).get("effects", {}),
             "story": (_find_card(cid, current_world) or {}).get("story", "")}
            for cid in player_state["cards"]
        ],
        "available_actions": get_available_actions(player_state, current_world),
        "starting_cards": [
            {"id": c["id"], "name": c["name"], "type": c["type"], "description": c["description"],
             "story": c.get("story", "")}
            for cid in player_state["cards"]
            for c in current_world.get("causality_cards", []) if c["id"] == cid
        ],
    })


@app.route("/api/action", methods=["POST"])
def handle_action():
    global current_world, player_state

    action_text = request.json.get("action", "").strip()
    if not action_text:
        return jsonify({"error": "行动不能为空"}), 400

    # ── 状态修改必须在锁内完成（因果引擎 + 时间跳跃）──
    with state_lock:
        if not current_world:
            return jsonify({"error": "请先加载世界"}), 400
        if not player_state:
            return jsonify({"error": "玩家状态未初始化"}), 400

        # 特殊处理：时间跳跃（等待到午夜）
        if action_text == "我等到午夜时分":
            current_hour = (player_state["game_time"] // 60) % 24
            if current_hour < 21 and current_hour >= 6:
                # 快进到 21:00
                player_state["game_time"] = 21 * 60
                loc_data = _find_location(player_state["current_location"], current_world)
                loc_name = loc_data.get("name", "未知地点") if loc_data else ""
                # 在锁内构建响应（此路径不经过因果引擎，直接返回）
                actions = get_available_actions(player_state, current_world)
                return jsonify({
                    "narrative": f"你在{loc_name}消磨了时间。天色渐渐暗下来——北面森林的风变冷了，酒馆的窗户透出暖黄的灯光。村口的碎石在月光下泛着灰白。\n\n午夜近了。玛莎说过——后门，别让任何人看见。",
                    "action_raw": action_text,
                    "is_ending": False,
                    "causal_meta": ["时间快进至 21:00，午夜将近"],
                    "dice_result": None,
                    "new_cards": [],
                    "current_location_id": player_state["current_location"],
                    "locations": {lid: ld["name"] for lid, ld in current_world.get("locations", {}).items()},
                    "game_hour": 21,
                    "npcs": [
                        {"id": n["id"], "name": n["name"], "role": n["role"],
                         "location": n["location"],
                         "alive": player_state["npc_alive"].get(n["id"], True),
                         "attitude": player_state["npc_attitudes"].get(n["id"], 0),
                         "suspicion": player_state.get("npc_suspicion", {}).get(n["id"], 0)}
                        for n in current_world["npcs"]
                    ],
                    "npc_states": {
                        n["id"]: {
                            "name": n["name"], "role": n["role"],
                            "alive": player_state["npc_alive"].get(n["id"], True),
                            "attitude": player_state["npc_attitudes"].get(n["id"], 0),
                        }
                        for n in current_world["npcs"]
                    },
                    "player_cards": [
                        {"id": cid, "name": (_find_card(cid, current_world) or {}).get("name", cid),
                         "type": (_find_card(cid, current_world) or {}).get("type", "unknown"),
                         "description": (_find_card(cid, current_world) or {}).get("description", "")}
                        for cid in player_state.get("cards", [])
                    ],
                    "current_location": loc_name,
                    "game_time": "21:00",
                    "available_actions": actions,
                })

        # 运行因果引擎（在锁内——会修改 player_state）
        result = run_causal_engine(action_text, current_world, player_state)

        # 更新玩家当前位置
        action = result["action"]
        if action.get("target_location"):
            player_state["current_location"] = action["target_location"]


    narrative = render_with_deepseek_narrative(result, current_world, player_state)
    if not narrative:
        narrative = build_fallback_narrative(result, current_world, player_state)

    causal_meta = []
    if result.get("dice_result"):
        dr = result["dice_result"]
        status_text = "\u6210\u529f" if dr["success"] else "\u53d7\u963b"
        causal_meta.append(f"\u547d\u8fd0\u5224\u5b9a\uff1a{status_text}\u3002\u4f60\u7684\u884c\u52a8\u5728\u8fd9\u4e00\u523b\u6539\u53d8\u4e86\u5c40\u9762\u3002")
    if result.get("card_matched"):
        version_names = {"warm": "\u5173\u7cfb\u6709\u6240\u56de\u5e94", "cold": "\u5c40\u9762\u53d8\u5f97\u7d27\u5f20", "neutral": "\u573a\u666f\u7ee7\u7eed\u63a8\u8fdb"}
        default_branch = "\u573a\u666f\u7ee7\u7eed\u63a8\u8fdb"
        causal_meta.append(f"\u53d9\u4e8b\u5206\u652f\uff1a{version_names.get(result.get('version', ''), default_branch)}")
    if result.get("new_cards"):
        for c in result["new_cards"]:
            type_names = {"relation": "\u5173\u7cfb", "knowledge": "\u7ebf\u7d22", "item": "\u7269\u54c1", "crime": "\u7f6a\u75d5"}
            tn = type_names.get(c.get("type", ""), c.get("type", ""))
            causal_meta.append(f"\u65b0\u7684\u56e0\u679c\uff1a{tn}\u300a{c['name']}\u300b")
    ai_j = result.get("ai_judgement") or {}
    if ai_j.get("used"):
        feas_names = {"possible": "\u53ef\u884c", "risky": "\u6709\u98ce\u9669", "impossible": "\u4e0d\u6210\u7acb", "meta": "\u8d8a\u754c"}
        reason = ai_j.get("reason", "")
        causal_meta.append(f"\u4e16\u754c\u5224\u65ad\uff1a{feas_names.get(ai_j.get('feasibility'), ai_j.get('feasibility'))} - {reason}")
        if ai_j.get("memory"):
            causal_meta.append(f"\u8bb0\u5fc6\u523b\u75d5\uff1a{ai_j['memory']}")
    if result.get("no_causal_match") or (not result.get("card_matched") and not result.get("dice_result")):
        causal_meta.append("\u8fd9\u6b21\u884c\u52a8\u6ca1\u6709\u6253\u5f00\u5173\u952e\u7ebf\u7d22\uff0c\u4f46\u4e16\u754c\u8bb0\u4f4f\u4e86\u4f60\u7684\u8bd5\u63a2\u3002")

    is_ending = result.get("ending") is not None

    return jsonify({
        "narrative": narrative,
        "action_raw": action_text,
        "card_matched": result.get("card_matched"),
        "version": result.get("version"),
        "is_ending": is_ending,
        "causal_meta": causal_meta,
        "ai_judgement": result.get("ai_judgement"),
        "ai_memories": player_state.get("ai_memories", [])[-8:],
        "ending": {
            "id": result["ending"]["id"],
            "name": result["ending"]["name"],
        } if result.get("ending") else None,
        "dice_result": result.get("dice_result"),
        "new_cards": result.get("new_cards", []),
        "current_location_id": player_state["current_location"],
        "locations": {lid: ld["name"] for lid, ld in current_world.get("locations", {}).items()},
        "game_hour": (player_state["game_time"] // 60) % 24,
        "npcs": [
            {"id": n["id"], "name": n["name"], "role": n["role"],
             "location": n["location"],
             "alive": player_state["npc_alive"].get(n["id"], True),
             "attitude": player_state["npc_attitudes"].get(n["id"], 0),
             "suspicion": player_state.get("npc_suspicion", {}).get(n["id"], 0)}
            for n in current_world["npcs"]
        ],
        "npc_states": {
            n["id"]: {
                "name": n["name"],
                "role": n["role"],
                "alive": player_state["npc_alive"].get(n["id"], True),
                "attitude": player_state["npc_attitudes"].get(n["id"], 0),
                "suspicion": player_state.get("npc_suspicion", {}).get(n["id"], 0),
            }
            for n in current_world["npcs"]
        },
        "player_cards": [
            {"id": cid, "name": (_find_card(cid, current_world) or {}).get("name", cid),
             "type": (_find_card(cid, current_world) or {}).get("type", "unknown"),
             "description": (_find_card(cid, current_world) or {}).get("description", "")}
            for cid in player_state.get("cards", [])
        ],
        "current_location": _find_location(player_state["current_location"], current_world).get("name", ""),
        "game_time": f"{player_state['game_time'] // 60 % 24:02d}:{player_state['game_time'] % 60:02d}",
        "available_actions": get_available_actions(player_state, current_world) if not is_ending else [],
    })


@app.route("/api/state", methods=["GET"])
def get_state():
    if not current_world or not player_state:
        return jsonify({"error": "未加载世界"}), 400

    return jsonify({
        "world": current_world["name"],
        "player_name": player_state["name"],
        "attributes": player_state["attributes"],
        "game_time": f"{player_state['game_time'] // 60 % 24:02d}:{player_state['game_time'] % 60:02d}",
        "game_hour": (player_state["game_time"] // 60) % 24,
        "current_location": _find_location(player_state["current_location"], current_world).get("name", ""),
        "current_location_id": player_state["current_location"],
        "locations": {lid: ld["name"] for lid, ld in current_world.get("locations", {}).items()},
        "ai_memories": player_state.get("ai_memories", [])[-8:],
        "npcs": [
            {"id": n["id"], "name": n["name"], "role": n["role"],
             "location": n["location"],
             "alive": player_state["npc_alive"].get(n["id"], True),
             "attitude": player_state["npc_attitudes"].get(n["id"], 0),
             "suspicion": player_state.get("npc_suspicion", {}).get(n["id"], 0)}
            for n in current_world["npcs"]
        ],
        "npc_states": {
            n["id"]: {
                "name": n["name"],
                "role": n["role"],
                "alive": player_state["npc_alive"].get(n["id"], True),
                "attitude": player_state["npc_attitudes"].get(n["id"], 0),
                "suspicion": player_state.get("npc_suspicion", {}).get(n["id"], 0),
            }
            for n in current_world["npcs"]
        },
        "player_cards": [
            {"id": cid, "name": (_find_card(cid, current_world) or {}).get("name", cid),
             "type": (_find_card(cid, current_world) or {}).get("type", "unknown"),
             "description": (_find_card(cid, current_world) or {}).get("description", ""),
             "story": (_find_card(cid, current_world) or {}).get("story", "")}
            for cid in player_state.get("cards", [])
        ],
    })


if __name__ == "__main__":
    import sys
    print("织梦者 · Dream Weaver — 因果叙事引擎")
    print("DeepSeek ????????????????")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5002
    app.run(host="127.0.0.1", port=port, debug=False)
