from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
DATA = ROOT / "data"
MEDIA = DATA / "media"
DB_PATH = DATA / "provenance.db"
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8010"))
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def palette(image: Image.Image) -> list[str]:
    reduced = image.convert("RGB").resize((80, 80)).quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    colors = reduced.getcolors() or []
    raw = reduced.getpalette() or []
    ranked = sorted(colors, reverse=True)[:5]
    return ["#{:02x}{:02x}{:02x}".format(*raw[index * 3:index * 3 + 3]) for _, index in ranked]


def average_color(colors: list[str]) -> str:
    if not colors:
        return "#000000"
    values = [tuple(int(color[i:i + 2], 16) for i in (1, 3, 5)) for color in colors]
    value = tuple(sum(item[i] for item in values) // len(values) for i in range(3))
    return "#{:02x}{:02x}{:02x}".format(*value)


def perceptual_hash(image: Image.Image) -> str:
    small = ImageOps.grayscale(image).resize((8, 8), Image.Resampling.LANCZOS)
    values = list(small.getdata())
    threshold = sum(values) / len(values)
    return "".join("1" if value >= threshold else "0" for value in values)


def hamming(a: str, b: str) -> int:
    return sum(left != right for left, right in zip(a, b)) + abs(len(a) - len(b))


def image_analysis(blob: bytes) -> dict:
    with Image.open(BytesIO(blob)) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        colors = palette(image)
        exif = {}
        for key, value in opened.getexif().items():
            if isinstance(value, (str, int, float)):
                exif[str(key)] = value
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "colors": colors,
            "average_color": average_color(colors),
            "phash": perceptual_hash(image),
            "exif": exif,
        }


def make_seed_art(path: Path, variation: int) -> None:
    width, height = 1200, 720
    base = Image.new("RGB", (width, height), (8 + variation * 3, 20 + variation * 5, 36 + variation * 7))
    draw = ImageDraw.Draw(base, "RGBA")
    for y in range(height):
        depth = y / height
        color = (7 + int(14 * depth), 26 + int(46 * depth), 50 + int(62 * depth), 255)
        draw.line((0, y, width, y), fill=color)
    halo_x, halo_y = 650 + variation * 42, 320 - variation * 20
    for radius in range(380, 20, -12):
        alpha = max(1, int(0.7 * (400 - radius)))
        draw.ellipse((halo_x - radius, halo_y - radius, halo_x + radius, halo_y + radius), fill=(26, 190, 207, alpha))
    draw.polygon([(0, 720), (0, 420), (260, 350), (475, 490), (690, 300), (960, 450), (1200, 375), (1200, 720)], fill=(5, 14, 23, 245))
    if variation >= 1:
        draw.ellipse((460, 95, 850, 650), outline=(87, 226, 225, 165), width=10)
    if variation >= 2:
        draw.line((300, 610, 790, 155), fill=(236, 177, 92, 200), width=12)
        draw.line((370, 640, 860, 185), fill=(236, 177, 92, 65), width=35)
    if variation >= 3:
        draw.rectangle((72, 72, 1128, 648), outline=(189, 243, 230, 150), width=3)
        draw.text((92, 96), "ABYSSAL ARCHIVE / FINAL", fill=(216, 244, 237, 210), stroke_width=1)
    base = base.filter(ImageFilter.GaussianBlur(radius=max(0, 2 - variation)))
    base.save(path, "PNG", optimize=True)


def initialize() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    MEDIA.mkdir(parents=True, exist_ok=True)
    with db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filename TEXT NOT NULL,
                mime TEXT NOT NULL,
                bytes INTEGER NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                mode TEXT NOT NULL,
                colors TEXT NOT NULL,
                average_color TEXT NOT NULL,
                phash TEXT NOT NULL,
                exif TEXT NOT NULL,
                parent_id INTEGER,
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_seed INTEGER NOT NULL DEFAULT 0,
                storage_kind TEXT NOT NULL DEFAULT 'upload',
                source_url TEXT NOT NULL DEFAULT '',
                source_license TEXT NOT NULL DEFAULT '',
                source_credit TEXT NOT NULL DEFAULT ''
            )
        """)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(assets)").fetchall()}
        for name, definition in {
            "storage_kind": "TEXT NOT NULL DEFAULT 'upload'",
            "source_url": "TEXT NOT NULL DEFAULT ''",
            "source_license": "TEXT NOT NULL DEFAULT ''",
            "source_credit": "TEXT NOT NULL DEFAULT ''",
            "project": "TEXT NOT NULL DEFAULT '未归档项目'",
            "tags": "TEXT NOT NULL DEFAULT '[]'",
        }.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE assets ADD COLUMN {name} {definition}")
        connection.execute("UPDATE assets SET project = '深海遗墟' WHERE is_seed = 1 AND storage_kind = 'upload' AND project = '未归档项目'")
        connection.execute("UPDATE assets SET project = '公共参考素材库' WHERE storage_kind = 'reference' AND project = '未归档项目'")
        count = connection.execute("SELECT COUNT(*) FROM assets WHERE is_seed = 1").fetchone()[0]
        titles = [] if count else ["原始构图 / Reef Signal", "色彩探索 / Cyan Bloom", "镜头校准 / Amber Cut", "定稿 / Abyssal Archive"]
        notes = [] if count else [
            "从深海遗墟的构图草案开始，记录空间层级与中心光源。",
            "保留构图，提升冷青色的发光面积，测试主体的可读性。",
            "加入琥珀色动线作为第二层叙事信号，避免全画面同温。",
            "收束为定稿：压低背景信息密度，保留可识别的门形轮廓。",
        ]
        parent = None
        for index, (title, note) in enumerate(zip(titles, notes)):
            filename = f"seed-abyss-{index + 1}.png"
            target = MEDIA / filename
            make_seed_art(target, index)
            blob = target.read_bytes()
            result = image_analysis(blob)
            cursor = connection.execute("""
                INSERT INTO assets (title, filename, mime, bytes, width, height, mode, colors, average_color, phash, exif, parent_id, notes, created_at, is_seed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (title, filename, "image/png", len(blob), result["width"], result["height"], result["mode"], json.dumps(result["colors"]), result["average_color"], result["phash"], json.dumps(result["exif"]), parent, note, now()))
            parent = cursor.lastrowid

        references = [
            ("公开参考 / Underwater coral reef", "coral-reef-jerry-reid.jpg", "https://commons.wikimedia.org/wiki/File:Underwater_photo_of_coral_reef.jpg", "Public Domain", "Jerry Reid / U.S. Fish and Wildlife Service"),
            ("公开参考 / ROV and coral", "rov-retriever-seamount-noaa.jpg", "https://commons.wikimedia.org/wiki/File:ROV_and_coral_-_Retriever_Seamount.jpg", "Public Domain", "NOAA Office of Ocean Exploration and Research"),
            ("公开参考 / Tutuila coral reef", "tutuila-coral-reef-usgs.jpg", "https://www.usgs.gov/media/images/underwater-photo-coral-reef-tutuila-island", "Public Domain", "Curt Storlazzi / USGS Pacific Coastal and Marine Science Center"),
        ]
        static_reference_dir = FRONTEND / "assets" / "public-domain"
        for title, filename, source_url, source_license, source_credit in references:
            exists = connection.execute("SELECT id FROM assets WHERE filename = ? AND storage_kind = 'reference'", (filename,)).fetchone()
            if exists:
                continue
            blob = (static_reference_dir / filename).read_bytes()
            result = image_analysis(blob)
            connection.execute("""
                INSERT INTO assets (title, filename, mime, bytes, width, height, mode, colors, average_color, phash, exif, parent_id, notes, created_at, is_seed, storage_kind, source_url, source_license, source_credit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, 1, 'reference', ?, ?, ?)
            """, (title, filename, "image/jpeg", len(blob), result["width"], result["height"], result["mode"], json.dumps(result["colors"]), result["average_color"], result["phash"], json.dumps(result["exif"]), "公共领域参考素材。来源、作者/机构与许可信息均保留在本档案中；它不是作品集作者的原创素材。", now(), source_url, source_license, source_credit))


def asset_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    result["colors"] = json.loads(result["colors"])
    result["exif"] = json.loads(result["exif"])
    result["tags"] = json.loads(result["tags"] or "[]")
    result["url"] = f"/assets/public-domain/{result['filename']}" if result["storage_kind"] == "reference" else f"/media/{result['filename']}"
    result["has_exif"] = bool(result["exif"])
    return result


def list_assets(query: str = "", tag: str = "", project: str = "") -> list[dict]:
    with db() as connection:
        rows = connection.execute("SELECT * FROM assets ORDER BY id DESC").fetchall()
    records = [asset_dict(row) for row in rows]
    query = query.strip().lower()
    return [record for record in records if (not query or query in record["title"].lower() or query in record["notes"].lower()) and (not tag or tag in record["tags"]) and (not project or project == record["project"])]


def add_asset(payload: dict) -> dict:
    title = str(payload.get("title") or "未命名版本").strip()[:80]
    source = str(payload.get("data_url") or "")
    if not source.startswith("data:image/") or "," not in source:
        raise ValueError("请上传 PNG、JPG、WEBP 或 GIF 图片。")
    header, encoded = source.split(",", 1)
    try:
        blob = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise ValueError("图片数据无法读取。") from error
    if not blob or len(blob) > MAX_UPLOAD_BYTES:
        raise ValueError("图片必须小于 8 MB。")
    try:
        result = image_analysis(blob)
    except Exception as error:
        raise ValueError("文件不是可读取的图片，或图片已损坏。") from error
    digest = hashlib.sha256(blob).hexdigest()[:14]
    tags = [str(tag).strip()[:24] for tag in payload.get("tags", []) if str(tag).strip()][:8]
    project = str(payload.get("project") or "未归档项目").strip()[:48]
    with db() as connection:
        duplicate = connection.execute("SELECT id FROM assets WHERE filename LIKE ?", (f"{digest}%",)).fetchone()
        if duplicate:
            raise ValueError(f"这张图片已存在，档案编号为 #{duplicate['id']}。")
        parent_id = payload.get("parent_id")
        if parent_id is not None:
            parent = connection.execute("SELECT id FROM assets WHERE id = ?", (parent_id,)).fetchone()
            if not parent:
                raise ValueError("选择的父版本不存在。")
        extension = ".png"
        filename = f"{digest}{extension}"
        (MEDIA / filename).write_bytes(blob)
        cursor = connection.execute("""
            INSERT INTO assets (title, filename, mime, bytes, width, height, mode, colors, average_color, phash, exif, parent_id, notes, created_at, is_seed, project, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (title, filename, header.split(";")[0].replace("data:", ""), len(blob), result["width"], result["height"], result["mode"], json.dumps(result["colors"]), result["average_color"], result["phash"], json.dumps(result["exif"]), parent_id, str(payload.get("notes") or "").strip()[:600], now(), project, json.dumps(tags)))
        row = connection.execute("SELECT * FROM assets WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return asset_dict(row)


def update_asset(asset_id: int, payload: dict) -> dict:
    allowed = {"title", "notes", "parent_id", "project", "tags"}
    if not any(key in payload for key in allowed):
        raise ValueError("没有可更新的字段。")
    with db() as connection:
        row = connection.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        if not row:
            raise ValueError("档案不存在。")
        title = str(payload.get("title", row["title"])).strip()[:80] or row["title"]
        notes = str(payload.get("notes", row["notes"])).strip()[:600]
        project = str(payload.get("project", row["project"])).strip()[:48] or "未归档项目"
        tags = [str(tag).strip()[:24] for tag in payload.get("tags", json.loads(row["tags"] or "[]")) if str(tag).strip()][:8]
        parent_id = payload.get("parent_id", row["parent_id"])
        if parent_id == asset_id:
            raise ValueError("版本不能将自己设为父版本。")
        if parent_id is not None and not connection.execute("SELECT id FROM assets WHERE id = ?", (parent_id,)).fetchone():
            raise ValueError("选择的父版本不存在。")
        connection.execute("UPDATE assets SET title=?, notes=?, parent_id=?, project=?, tags=? WHERE id=?", (title, notes, parent_id, project, json.dumps(tags), asset_id))
        return asset_dict(connection.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone())


def delete_asset(asset_id: int) -> None:
    with db() as connection:
        row = connection.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        if not row:
            raise ValueError("档案不存在。")
        if row["is_seed"] or row["storage_kind"] == "reference":
            raise ValueError("演示和公开参考档案受保护，不能删除。")
        connection.execute("UPDATE assets SET parent_id = NULL WHERE parent_id = ?", (asset_id,))
        connection.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    (MEDIA / row["filename"]).unlink(missing_ok=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def json(self, status: int, value: dict | list) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/assets":
            query = parse_qs(parsed.query)
            self.json(HTTPStatus.OK, {"assets": list_assets(query.get("q", [""])[0], query.get("tag", [""])[0], query.get("project", [""])[0]), "storage": "temporary"})
            return
        if parsed.path == "/api/report":
            records = list_assets()
            self.json(HTTPStatus.OK, {"generated_at": now(), "total_assets": len(records), "projects": sorted({record["project"] for record in records}), "tags": sorted({tag for record in records for tag in record["tags"]}), "assets": records})
            return
        if parsed.path == "/api/compare":
            query = parse_qs(parsed.query)
            try:
                first, second = int(query["a"][0]), int(query["b"][0])
                with db() as connection:
                    rows = connection.execute("SELECT * FROM assets WHERE id IN (?, ?)", (first, second)).fetchall()
                if len(rows) != 2:
                    raise ValueError
                records = {row["id"]: asset_dict(row) for row in rows}
                distance = hamming(records[first]["phash"], records[second]["phash"])
                similarity = round(max(0, 100 - distance / 64 * 100), 1)
                self.json(HTTPStatus.OK, {"a": records[first], "b": records[second], "similarity": similarity, "method": "8x8 perceptual hash"})
            except (KeyError, ValueError, IndexError):
                self.json(HTTPStatus.BAD_REQUEST, {"error": "请选择两个存在的版本。"})
            return
        if parsed.path.startswith("/media/"):
            self.serve_file(MEDIA / Path(parsed.path).name)
            return
        self.serve_file(FRONTEND / ("index.html" if parsed.path in ("/", "") else parsed.path.lstrip("/")))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/api/assets", "/api/assets/batch"):
            self.json(HTTPStatus.NOT_FOUND, {"error": "接口不存在。"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_UPLOAD_BYTES * 2:
                raise ValueError("请求体大小不符合要求。")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if path == "/api/assets/batch":
                created, errors = [], []
                for index, item in enumerate(payload.get("assets", [])):
                    try:
                        created.append(add_asset(item))
                    except ValueError as error:
                        errors.append({"index": index, "error": str(error)})
                self.json(HTTPStatus.CREATED, {"assets": created, "errors": errors})
            else:
                self.json(HTTPStatus.CREATED, {"asset": add_asset(payload)})
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            self.json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def do_PUT(self) -> None:
        try:
            asset_id = int(urlparse(self.path).path.rsplit("/", 1)[-1])
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self.json(HTTPStatus.OK, {"asset": update_asset(asset_id, payload)})
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self.json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def do_DELETE(self) -> None:
        try:
            asset_id = int(urlparse(self.path).path.rsplit("/", 1)[-1])
            delete_asset(asset_id)
            self.json(HTTPStatus.OK, {"deleted": asset_id})
        except ValueError as error:
            self.json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def serve_file(self, path: Path) -> None:
        try:
            path = path.resolve()
            if not (str(path).startswith(str(FRONTEND.resolve())) or str(path).startswith(str(MEDIA.resolve()))) or not path.is_file():
                raise FileNotFoundError
            body = path.read_bytes()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")


if __name__ == "__main__":
    initialize()
    print(f"Creative Provenance Lab running at http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
