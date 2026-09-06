from __future__ import annotations

import json
import random
import re
import sqlite3
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DATA = ROOT / "data"
DB_PATH = DATA / "concepts.db"
HOST = "127.0.0.1"
PORT = 8000
MAX_BODY_BYTES = 64 * 1024   # 单次请求体上限，避免异常大 body 占用内存
MAX_BRIEF_LEN = 500          # 创作简述长度上限


def ensure_db() -> None:
    DATA.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                brief TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )


def clean_words(text: str) -> list[str]:
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    stop = {"the", "and", "with", "for", "a", "an", "of", "in", "to", "一个", "一种", "以及", "和"}
    return [t for t in tokens if t not in stop][:10]


PALETTES = [
    {
        "name": "Ion Glass",
        "colors": ["#E8FAFF", "#62D8FF", "#FFCF66", "#17212B", "#F46A6A"],
        "mood": "清透、锋利、带有高能实验室的冷光感",
    },
    {
        "name": "Nocturne Signal",
        "colors": ["#101318", "#36F5B2", "#EAF0FF", "#E3487A", "#F6B95E"],
        "mood": "夜间信号、潮湿金属、霓虹边缘和高反差剪影",
    },
    {
        "name": "Solar Archive",
        "colors": ["#FFF4D7", "#FF8A3D", "#3547E8", "#111827", "#7BE0AD"],
        "mood": "档案室、太阳尘埃、工业蓝和温暖扫描光",
    },
    {
        "name": "Bio Circuit",
        "colors": ["#F2FFE8", "#00C27A", "#1C2A32", "#B963FF", "#FFD166"],
        "mood": "生物结构与电路系统融合，像有生命的界面",
    },
]

ARCHETYPES = [
    {
        "label": "沉浸式空间",
        "structure": "入口区 -> 观察廊 -> 核心装置 -> 资料层",
        "camera": "低机位推进，随后绕核心物体做 120 度弧形环绕",
    },
    {
        "label": "品牌概念片",
        "structure": "黑场标题 -> 材质微距 -> 产品/空间显形 -> 标语定格",
        "camera": "微距切入，快速拉远形成尺度反差",
    },
    {
        "label": "游戏关卡提案",
        "structure": "出生点 -> 视觉地标 -> 风险路径 -> 奖励区域",
        "camera": "俯视建立路径，再切到肩后视角制造进入感",
    },
    {
        "label": "展览策展方案",
        "structure": "主题墙 -> 分区叙事 -> 交互台 -> 纪念出口",
        "camera": "稳定横移，像观众沿展墙缓慢浏览",
    },
]

AUDIENCES = [
    "AIGC 概念艺术作品集",
    "品牌视觉提案",
    "游戏 / 影视前期设定",
    "交互展览策划",
]

MATERIALS = [
    "半透明树脂", "阳极氧化铝", "雾面陶瓷", "湿润沥青", "发光纤维",
    "磨砂玻璃", "碳纤维织纹", "液态金属", "投影薄雾", "再生塑料"
]

LIGHTING = [
    "顶部窄束冷光与地面反射光形成双层照明",
    "侧后方强轮廓光压出剪影，局部用暖色扫描线破开暗部",
    "低饱和环境光铺底，关键物体使用脉冲式强调光",
    "柔和天光混合硬边投影，制造真实空间和概念感的平衡",
]

COPY_ANGLES = [
    "让抽象主题变成可被观看、解释和继续生产的视觉系统。",
    "把一段灵感拆解为色彩、材质、镜头、空间和生成提示词。",
    "不是单张图的灵感，而是一套可以继续扩展的 AIGC 创作方向。",
    "以可视化 brief 为核心，让概念从一句话长成一个小型世界。",
]

OUTPUT_FORMATS = [
    "一页式视觉提案板",
    "15 秒概念短片分镜",
    "可交互网页首屏",
    "三张系列概念图",
]


def pick(rng: random.Random, items: list):
    return items[rng.randrange(len(items))]


def generate_concept(brief: str) -> dict:
    words = clean_words(brief)
    seed_text = brief.strip() or str(time.time())
    seed = sum(ord(ch) for ch in seed_text)
    rng = random.Random(seed)
    palette = pick(rng, PALETTES)
    archetype = pick(rng, ARCHETYPES)
    selected_materials = rng.sample(MATERIALS, 4)
    audience = pick(rng, AUDIENCES)
    output_format = pick(rng, OUTPUT_FORMATS)
    title_words = words[:3] if words else ["unknown", "signal"]
    title = " / ".join(w.upper() for w in title_words)

    main_subject = brief.strip() or "未来东方美术馆"
    keywords = list(dict.fromkeys(words + rng.sample([
        "aigc", "concept", "prototype", "cinematic", "spatial", "ritual",
        "modular", "artifact", "interface", "atmosphere"
    ], 6)))[:12]

    prompt = (
        f"{main_subject}, {archetype['label']}, cinematic concept design, "
        f"{palette['mood']}, materials: {', '.join(selected_materials)}, "
        f"composition with layered depth, human scale reference, precise lighting, "
        f"high-detail visual development board, production design, 16:9"
    )

    return {
        "title": title,
        "subtitle": pick(rng, COPY_ANGLES),
        "archetype": archetype["label"],
        "audience": audience,
        "output_format": output_format,
        "creative_thesis": (
            f"核心判断：把“{main_subject}”从一句灵感推进成一个可生产的 AIGC 视觉母题。"
            f"第一眼要抓住{palette['mood']}，第二眼要能读出空间叙事，第三眼要让观众相信它可以继续生长。"
        ),
        "worldview": (
            f"这个方案把“{main_subject}”处理成一个可扩展的视觉系统："
            f"它不是单点画面，而是围绕“{archetype['structure']}”组织的叙事空间。"
            f"整体气质偏向{palette['mood']}，适合继续延展成系列图、概念短片或交互网页。"
        ),
        "keywords": keywords,
        "palette": palette,
        "materials": selected_materials,
        "spatial_logic": archetype["structure"],
        "lighting": pick(rng, LIGHTING),
        "camera_language": archetype["camera"],
        "composition": [
            "前景放置一个可识别的尺度物，避免画面只剩抽象氛围。",
            "中景建立主要结构，让观众快速理解空间功能。",
            "远景用光源、门洞或标识形成视觉锚点。",
        ],
        "image_prompt": prompt,
        "prompt_variants": [
            f"{main_subject}, editorial key visual, {palette['mood']}, clean composition, design award presentation",
            f"{main_subject}, environment concept art, layered architecture, {', '.join(selected_materials[:2])}, cinematic lighting",
            f"{main_subject}, interactive installation design, human scale, atmospheric particles, technical visual board",
        ],
        "negative_prompt": (
            "low quality, blurry, messy composition, overexposed, flat lighting, "
            "generic sci-fi, random text, duplicated objects, bad perspective"
        ),
        "video_direction": [
            "0-3s：用材质微距建立质感和尺度。",
            "3-7s：镜头推进到主视觉装置，出现第一层空间结构。",
            "7-12s：灯光发生一次状态切换，暴露隐藏的信息层。",
            "12-15s：定格在标题画面，保留适合剪辑的尾帧。",
        ],
        "production_notes": [
            f"先用 {output_format} 做成可展示的最小闭环，避免一开始铺太大。",
            "图片生成阶段优先控制构图和材质，不急着追求细碎细节。",
            "网页展示时把 Prompt、迭代思路和最终视觉放在同一叙事里，增强作品集可信度。",
        ],
        "three_mood": {
            "palette": palette["colors"],
            "density": rng.randint(38, 72),
            "height": rng.randint(24, 64),
            "speed": round(rng.uniform(0.35, 0.9), 2),
            "grid": rng.choice(["radial", "corridor", "archive", "tower"]),
        },
    }


def save_concept(brief: str, result: dict) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "INSERT INTO concepts (created_at, brief, result_json) VALUES (?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), brief, json.dumps(result, ensure_ascii=False)),
        )
        return int(cursor.lastrowid)


def list_concepts() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, created_at, brief, result_json FROM concepts ORDER BY id DESC LIMIT 24"
        ).fetchall()
    concepts = []
    for row in rows:
        result = json.loads(row[3])
        concepts.append({
            "id": row[0],
            "created_at": row[1],
            "brief": row[2],
            "title": result.get("title", "UNTITLED"),
            "archetype": result.get("archetype", ""),
            "palette": result.get("palette", {}),
        })
    return concepts


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def send_json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/concepts":
            self.send_json(list_concepts())
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/generate":
            self.send_json({"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError):
            self.send_json({"error": "非法请求头。"}, 400)
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self.close_connection = True
            try:
                self.rfile.read(min(max(length, 0), MAX_BODY_BYTES))
            except Exception:
                pass
            self.send_json({"error": "请求体为空或超出大小上限。"}, 400)
            return
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return
        brief = str(payload.get("brief", "")).strip()
        if len(brief) < 2:
            self.send_json({"error": "请先输入一个更具体的创意主题。"}, 400)
            return
        if len(brief) > MAX_BRIEF_LEN:
            self.send_json({"error": "主题请控制在 500 字以内。"}, 400)
            return
        result = generate_concept(brief)
        concept_id = save_concept(brief, result)
        self.send_json({
            "id": concept_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "brief": brief,
            "result": result,
        })

    def serve_static(self, request_path: str) -> None:
        if request_path in ("", "/"):
            target = FRONTEND / "index.html"
        else:
            safe = request_path.lstrip("/").replace("/", "\\")
            target = (FRONTEND / safe).resolve()
            if FRONTEND.resolve() not in target.parents and target != FRONTEND.resolve():
                self.send_error(403)
                return
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".pdf": "application/pdf",
            ".glb": "model/gltf-binary",
        }.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ensure_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Creative Engine Lab running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()
