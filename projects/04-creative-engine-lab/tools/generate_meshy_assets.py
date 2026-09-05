"""Generate and download Meshy GLB assets for the portfolio stage.

Usage:
  setx MESHY_API_KEY "your_key"   # or set it in the current shell
  python tools/generate_meshy_assets.py

The script creates preview text-to-3D tasks, waits for completion, optionally
starts refine tasks when supported by the account/API response, then downloads
GLB assets into frontend/assets/models.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "assets" / "models"
MANIFEST = OUT / "manifest.json"
BASE = os.environ.get("MESHY_BASE_URL", "https://api.meshy.ai/openapi/v2")
API_KEY = os.environ.get("MESHY_API_KEY")
POLL_SECONDS = int(os.environ.get("MESHY_POLL_SECONDS", "12"))
TIMEOUT_SECONDS = int(os.environ.get("MESHY_TIMEOUT_SECONDS", "900"))

ASSETS = [
    {
        "id": "creator-avatar",
        "name": "Creator Avatar",
        "prompt": "stylized 3D bust of a young Asian creative technologist, premium portfolio mascot, clean expressive face, subtle black outfit, clay-render quality, production-ready game asset, no text, no logo, neutral pose",
        "negative_prompt": "low quality, horror, extra limbs, distorted face, text, watermark, messy topology, broken eyes, cheap toy",
    },
    {
        "id": "idea-reactor",
        "name": "Idea Reactor",
        "prompt": "futuristic AIGC idea reactor device, compact floating workstation core, glass chamber, metal rings, neon lime and cyan accents, premium sci-fi product design, clean topology, no text, no logo",
        "negative_prompt": "messy wires, random symbols, text, watermark, overcomplicated, flat, low quality",
    },
    {
        "id": "project-dossier",
        "name": "Project Dossier",
        "prompt": "sealed interactive project dossier case, black brushed metal and translucent glass, glowing archive strips, elegant portfolio artifact, cinematic 3D asset, no text, no logo",
        "negative_prompt": "paper text, readable words, watermark, skulls, monsters, low quality, noisy surface",
    },
]


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not API_KEY:
        raise SystemExit("MESHY_API_KEY is not set. Set it locally, then rerun this script.")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Meshy HTTP {exc.code}: {body}") from exc


def download(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "CreativeEngineLab/1.0"})
    with urllib.request.urlopen(req, timeout=180) as res:
        path.write_bytes(res.read())


def get_task_id(response: dict[str, Any]) -> str:
    task_id = response.get("result") or response.get("id") or response.get("task_id")
    if isinstance(task_id, dict):
        task_id = task_id.get("id") or task_id.get("task_id")
    if not task_id:
        raise RuntimeError(f"Could not find task id in response: {response}")
    return str(task_id)


def wait_task(task_id: str) -> dict[str, Any]:
    started = time.time()
    while True:
        task = request_json("GET", f"/text-to-3d/{task_id}")
        status = str(task.get("status") or task.get("state") or "").upper()
        print(f"  {task_id}: {status or 'UNKNOWN'}")
        if status in {"SUCCEEDED", "SUCCESS", "COMPLETED", "DONE"}:
            return task
        if status in {"FAILED", "ERROR", "CANCELED", "CANCELLED", "EXPIRED"}:
            raise RuntimeError(f"Task {task_id} failed: {task}")
        if time.time() - started > TIMEOUT_SECONDS:
            raise TimeoutError(f"Task {task_id} timed out after {TIMEOUT_SECONDS}s")
        time.sleep(POLL_SECONDS)


def find_glb(task: dict[str, Any]) -> str:
    # Meshy responses commonly expose model_urls.glb. Keep this tolerant so the
    # script survives small response-shape changes.
    candidates = [
        task.get("model_urls", {}).get("glb") if isinstance(task.get("model_urls"), dict) else None,
        task.get("model_url"),
        task.get("glb_url"),
        task.get("result", {}).get("model_urls", {}).get("glb") if isinstance(task.get("result"), dict) else None,
    ]
    for item in candidates:
        if isinstance(item, str) and item.startswith("http"):
            return item
    raise RuntimeError(f"No GLB URL found in task response: {json.dumps(task, ensure_ascii=False)[:1200]}")


def create_preview(asset: dict[str, str]) -> str:
    payload = {
        "mode": "preview",
        "prompt": asset["prompt"],
        "negative_prompt": asset["negative_prompt"],
        "art_style": "realistic",
        "should_remesh": True,
    }
    response = request_json("POST", "/text-to-3d", payload)
    return get_task_id(response)


def maybe_refine(preview_task: dict[str, Any]) -> dict[str, Any]:
    task_id = preview_task.get("id") or preview_task.get("task_id") or preview_task.get("result")
    if not task_id:
        return preview_task
    try:
        response = request_json("POST", "/text-to-3d", {"mode": "refine", "preview_task_id": str(task_id)})
        refine_id = get_task_id(response)
        print(f"  refine task: {refine_id}")
        return wait_task(refine_id)
    except Exception as exc:
        print(f"  refine skipped: {exc}")
        return preview_task


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for asset in ASSETS:
        target = OUT / f"{asset['id']}.glb"
        print(f"Generating {asset['name']}...")
        preview_id = create_preview(asset)
        preview_task = wait_task(preview_id)
        final_task = maybe_refine(preview_task)
        glb_url = find_glb(final_task)
        print(f"  downloading {target.name}")
        download(glb_url, target)
        manifest.append({"id": asset["id"], "name": asset["name"], "file": f"./assets/models/{target.name}"})
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {MANIFEST}")


if __name__ == "__main__":
    main()
