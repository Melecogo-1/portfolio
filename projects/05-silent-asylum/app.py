"""
《死寂疗养院》规则怪谈互动文字冒险游戏
Flask Web 应用主程序
"""
import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, session, jsonify, redirect, url_for

from game_data import (
    SCENES, FRAGMENTS, ENDINGS, BAD_ENDINGS,
    get_scene, get_fragment, get_ending, get_bad_ending,
    get_erosion_state, determine_ending,
    EROSION_STATES
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'silent-asylum-local-dev-key')
app.config['SAVES_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')

# ============================================================
# 游戏状态管理
# ============================================================

def create_new_game():
    """创建新游戏状态"""
    return {
        "erosion": 0,
        "fragments": [],
        "current_scene": 1,
        "current_event_index": 0,
        "no_cost_used": [],
        "flags": {},
        "game_over": False,
        "ending": None,
        "be_name": None,
        "show_rules": True,  # 进入新场景时显示规则
        "show_no_cost": False,  # 显示无代价降侵蚀选项
        "last_consequence": None,  # 上一个选择的后果文本
        "transition": False,  # 场景过渡中
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "save_name": "自动存档"
    }


def get_game_state():
    """从session获取游戏状态"""
    if 'game_state' not in session:
        session['game_state'] = create_new_game()
    return session['game_state']


def save_game_state(state):
    """保存游戏状态到session"""
    session['game_state'] = state


def finalize_assimilation(state, consequence=None):
    """把满侵蚀统一结算为同化结局。"""
    state["erosion"] = 100
    state["game_over"] = True
    state["ending"] = "assimilation"
    state["be_name"] = None
    if consequence is not None:
        state["last_consequence"] = consequence
    save_game_state(state)
    return get_ending("assimilation")


def save_to_file(state, slot=0):
    """将游戏状态保存到JSON文件"""
    os.makedirs(app.config['SAVES_DIR'], exist_ok=True)
    filepath = os.path.join(app.config['SAVES_DIR'], f'save_{slot}.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_from_file(slot=0):
    """从JSON文件读取游戏状态"""
    filepath = os.path.join(app.config['SAVES_DIR'], f'save_{slot}.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def get_all_saves():
    """获取所有存档信息"""
    saves = []
    for i in range(5):
        filepath = os.path.join(app.config['SAVES_DIR'], f'save_{i}.json')
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            saves.append({
                "slot": i,
                "scene": data.get("current_scene", 1),
                "erosion": data.get("erosion", 0),
                "fragments": len(data.get("fragments", [])),
                "time": data.get("created_at", "未知"),
                "name": data.get("save_name", "存档")
            })
    return saves


# ============================================================
# 路由
# ============================================================

@app.route('/')
def index():
    """主菜单页面"""
    saves = get_all_saves()
    return render_template('index.html', saves=saves)


@app.route('/new_game')
def new_game():
    """开始新游戏"""
    state = create_new_game()
    save_game_state(state)
    return redirect(url_for('game'))


@app.route('/load_game/<int:slot>')
def load_game(slot):
    """读取存档"""
    state = load_from_file(slot)
    if state:
        if not state.get("game_over") and state.get("erosion", 0) >= 100:
            finalize_assimilation(state, state.get("last_consequence"))
            return redirect(url_for('ending'))
        save_game_state(state)
        return redirect(url_for('game'))
    return redirect(url_for('index'))

@app.route('/game')
def game():
    """游戏主界面"""
    state = get_game_state()

    if not state.get("game_over") and state.get("erosion", 0) >= 100:
        finalize_assimilation(state, state.get("last_consequence"))
        return redirect(url_for('ending'))

    if state.get("game_over"):
        return redirect(url_for('ending'))

    scene = get_scene(state["current_scene"])
    if not scene:
        return redirect(url_for('ending'))

    # 获取当前侵蚀度状态
    erosion_state = get_erosion_state(state["erosion"])

    # 获取当前事件
    event_index = state["current_event_index"]
    current_event = None
    if event_index < len(scene["events"]):
        current_event = scene["events"][event_index]

    # 检查是否需要显示规则
    show_rules = state.get("show_rules", False)

    # 检查隐藏触发条件
    hidden_hint = None
    if state["current_scene"] == 3 and state["flags"].get("helped_man"):
        hidden_hint = "那个被你帮助过的男人从餐桌下偷偷塞给你一张皱巴巴的纸条，上面写着："
        '"别信写在前面的规则，留一口饭，别看林医生的眼睛。"'

    if state["current_scene"] == 4 and len(state["fragments"]) >= 9:
        hidden_hint = "你立刻注意到规则第8条和第11条的字迹比其他规则新得多，是后来被人强行覆盖贴上去的。"

    if state["current_scene"] == 5:
        if len(state["fragments"]) >= 12:
            hidden_hint = '地面上的白色粉笔字："不要信眼睛看到的，信影子。最后一条永远是对的。"'
        if len(state["fragments"]) >= 18:
            hidden_hint = (hidden_hint or '') + '\n你注意到规则第7条和第10条的字迹完全不同，且第10条的纸张边缘有明显的重叠痕迹。'

    return render_template(
        'game.html',
        state=state,
        scene=scene,
        erosion_state=erosion_state,
        current_event=current_event,
        show_rules=show_rules,
        hidden_hint=hidden_hint,
        fragments=FRAGMENTS,
        total_fragments=18
    )


@app.route('/choose', methods=['POST'])
def choose():
    """处理玩家选择"""
    state = get_game_state()
    data = request.get_json()

    choice_type = data.get('type', 'event')  # 'event', 'no_cost', 'close_rules'

    # 关闭规则显示
    if choice_type == 'close_rules':
        state["show_rules"] = False
        save_game_state(state)
        return jsonify({"status": "ok"})

    scene = get_scene(state["current_scene"])
    if not scene:
        return jsonify({"status": "error", "message": "场景数据错误"})

    # 处理无代价降侵蚀选项
    if choice_type == 'no_cost':
        reduction = scene.get("no_cost_reduction", {})
        if reduction and state["current_scene"] not in state["no_cost_used"]:
            erosion_change = reduction.get("erosion_change", -3)
            state["erosion"] = max(0, state["erosion"] + erosion_change)
            state["no_cost_used"].append(state["current_scene"])
            state["show_no_cost"] = False
            save_game_state(state)
            return jsonify({
                "status": "ok",
                "erosion_change": erosion_change,
                "new_erosion": state["erosion"],
                "consequence": f"你{reduction['description']}。\n→ 精神侵蚀度 {erosion_change}（当前：{state['erosion']}）"
            })

    # 处理事件选择
    if choice_type == 'event':
        event_index = state["current_event_index"]
        if event_index >= len(scene["events"]):
            return jsonify({"status": "error", "message": "事件索引错误"})

        event = scene["events"][event_index]
        choice_index = data.get('choice_index', 0)

        if choice_index >= len(event["choices"]):
            return jsonify({"status": "error", "message": "选项索引错误"})

        choice = event["choices"][choice_index]

        # 更新侵蚀度
        old_erosion = state["erosion"]
        state["erosion"] += choice["erosion_change"]
        state["erosion"] = max(0, min(100, state["erosion"]))

        # === 侵蚀度 >= 100，强制触发沉沦同化结局 ===
        if state["erosion"] >= 100:
            ending_data = finalize_assimilation(state, choice.get("consequence", ""))
            return jsonify({
                "status": "ok",
                "outcome": "assimilation",
                "erosion_change": choice["erosion_change"],
                "new_erosion": 100,
                "consequence": choice.get("consequence", ""),
                "ending": "assimilation",
                "ending_data": ending_data
            })

        # 更新碎片
        new_fragments = []
        for fid in choice.get("fragments", []):
            if fid not in state["fragments"]:
                state["fragments"].append(fid)
                new_fragments.append(fid)
        state["fragments"].sort()

        # 更新标记
        if "flag" in choice:
            state["flags"][choice["flag"]] = True

        # 保存后果文本
        state["last_consequence"] = choice.get("consequence", "")

        # 处理不同结果类型
        outcome = choice.get("outcome", "continue")

        result = {
            "status": "ok",
            "outcome": outcome,
            "erosion_change": choice["erosion_change"],
            "new_erosion": state["erosion"],
            "new_fragments": new_fragments,
            "total_fragments": len(state["fragments"]),
            "consequence": choice.get("consequence", ""),
            "erosion_state": get_erosion_state(state["erosion"]),
        }

        if outcome == "death":
            be_name = choice.get("be_name", "")
            be_data = get_bad_ending(be_name)
            state["game_over"] = True
            state["be_name"] = be_name
            state["ending"] = "bad_ending"
            # 自动存档（死亡前的场景存档可用于读档）
            save_game_state(state)
            result["be_name"] = be_name
            result["be_text"] = be_data["text"] if be_data else ""
            result["be_title"] = be_data["name"] if be_data else be_name

        elif outcome == "reset_s1":
            # 强制重置回场景一，但保留侵蚀度和碎片
            state["current_scene"] = 1
            state["current_event_index"] = 0
            state["show_rules"] = True
            state["show_no_cost"] = False
            state["last_consequence"] = choice.get("consequence", "")
            # 保留 no_cost_used，但场景一如果已经用过则不重复
            result["reset"] = True
            result["new_scene"] = 1

        elif outcome == "continue":
            # 推进到下一个事件
            state["current_event_index"] += 1
            # 检查是否完成了所有事件
            if state["current_event_index"] >= len(scene["events"]):
                # 场景完成，推进到下一场景
                if state["current_scene"] < 5:
                    # 自动存档
                    save_name = f"场景{state['current_scene']}完成"
                    state["save_name"] = save_name
                    save_to_file(state, state["current_scene"] - 1)
                    # 进入下一场景
                    state["current_scene"] += 1
                    state["current_event_index"] = 0
                    state["show_rules"] = True
                    state["show_no_cost"] = False
                    result["scene_complete"] = True
                    result["next_scene"] = state["current_scene"]
                    result["completion_text"] = scene.get("completion_text", "")
                else:
                    # 场景五完成，进入结局
                    result["scene_complete"] = True
                    state["game_over"] = True
                    ending_id = determine_ending(state["erosion"], len(state["fragments"]))
                    ending_data = get_ending(ending_id)
                    state["ending"] = ending_id
                    result["ending"] = ending_id
                    result["ending_data"] = ending_data

            # 检查是否需要显示无代价降侵蚀选项
            no_cost = scene.get("no_cost_reduction", {})
            trigger_event_idx = no_cost.get("trigger_event", -1)
            if (trigger_event_idx == state["current_event_index"] - 1 and
                state["current_scene"] not in state["no_cost_used"]):
                state["show_no_cost"] = True
                result["show_no_cost"] = True
                result["no_cost_desc"] = no_cost.get("condition_text", "")
                result["no_cost_option"] = no_cost.get("description", "")

        elif outcome == "ending":
            # 直接进入结局判定（场景五通风管道选择）
            state["game_over"] = True
            ending_id = determine_ending(state["erosion"], len(state["fragments"]))
            ending_data = get_ending(ending_id)
            state["ending"] = ending_id
            result["ending"] = ending_id
            result["ending_data"] = ending_data

        save_game_state(state)
        return jsonify(result)

    return jsonify({"status": "error", "message": "未知的请求类型"})


@app.route('/retry', methods=['POST'])
def retry():
    """死亡后重试：从当前事件重新开始"""
    state = get_game_state()
    state["game_over"] = False
    state["ending"] = None
    state["be_name"] = None
    state["last_consequence"] = None
    # 恢复到当前场景的当前事件
    save_game_state(state)
    return jsonify({"status": "ok"})


@app.route('/load_last_save', methods=['POST'])
def load_last_save():
    """死亡后读取最近存档"""
    state = get_game_state()
    current_scene = state.get("current_scene", 1)
    # 尝试读取当前场景的存档（场景开始时自动保存）
    # 如果没有，则读取上一个场景的存档
    for slot in range(current_scene - 1, -1, -1):
        loaded = load_from_file(slot)
        if loaded:
            loaded["game_over"] = False
            loaded["ending"] = None
            loaded["be_name"] = None
            loaded["last_consequence"] = None
            save_game_state(loaded)
            return jsonify({"status": "ok", "scene": loaded.get("current_scene", 1)})
    # 没有存档，从头开始
    state = create_new_game()
    save_game_state(state)
    return jsonify({"status": "ok", "scene": 1})


@app.route('/ending')
def ending():
    """结局页面"""
    state = get_game_state()

    if not state.get("game_over"):
        return redirect(url_for('game'))

    # 即死BE
    if state.get("ending") == "bad_ending":
        be_data = get_bad_ending(state.get("be_name", ""))
        return render_template('ending.html',
                             ending_type='bad',
                             title=be_data["name"] if be_data else "死亡",
                             text=be_data["text"] if be_data else "",
                             epilogue="",
                             erosion=state["erosion"],
                             fragments=len(state["fragments"]))

    # 正式结局
    ending_id = state.get("ending", "normal")
    ending_data = get_ending(ending_id)
    if not ending_data:
        ending_data = get_ending("normal")

    return render_template('ending.html',
                         ending_type=ending_id,
                         title=ending_data["name"],
                         text=ending_data["text"],
                         epilogue=ending_data["epilogue"],
                         erosion=state["erosion"],
                         fragments=len(state["fragments"]))


@app.route('/notes')
def notes():
    """碎片笔记页面（以JSON返回）"""
    state = get_game_state()
    fragment_data = {}
    for fid in state["fragments"]:
        frag = get_fragment(fid)
        if frag:
            fragment_data[fid] = frag
    return jsonify({
        "fragments": fragment_data,
        "total": 18,
        "collected": len(state["fragments"])
    })


@app.route('/save_manual', methods=['POST'])
def save_manual():
    """手动存档"""
    state = get_game_state()
    data = request.get_json() or {}
    slot = data.get('slot', state["current_scene"] - 1)
    state["save_name"] = f"手动存档 - 场景{state['current_scene']}"
    state["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_to_file(state, slot)
    return jsonify({"status": "ok", "slot": slot})


@app.route('/get_saves')
def get_saves():
    """获取所有存档列表"""
    saves = get_all_saves()
    return jsonify({"saves": saves})


# ============================================================
# 启动
# ============================================================
if __name__ == '__main__':
    os.makedirs(app.config['SAVES_DIR'], exist_ok=True)
    print("=" * 60)
    print("  《死寂疗养院》规则怪谈互动文字冒险游戏")
    print("  Silent Asylum - Rule Horror Interactive Fiction")
    print("=" * 60)
    print(f"  访问地址: http://127.0.0.1:8080")
    print(f"  存档目录: {app.config['SAVES_DIR']}")
    print("=" * 60)
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host=os.environ.get('HOST', '0.0.0.0'), port=int(os.environ.get('PORT', '8080')))
