from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from logger import logger

import io, os, zipfile, subprocess, re, time, json

from statics import ROOT, EXPERIMENTS_DIR

@dataclass(frozen=True)
class HandlerResult:
    status: int
    payload: Optional[Dict[str, Any]] = None   # for JSON
    text: Optional[str] = None                # for plain text errors
    headers: Dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class ExportResult:
    status: int
    content: Optional[bytes] = None
    media_type: Optional[str] = None
    headers: Dict[str, str] = None


async def export_experiment_data(file_name: str) -> ExportResult:
    if not file_name:
        return ExportResult(status=404)

    cap_dir = os.path.join(ROOT, "captures", file_name)
    ndjson_path = os.path.join(EXPERIMENTS_DIR, file_name, "testdata.ndjson")

    if not os.path.isdir(cap_dir) or not os.path.isfile(ndjson_path):
        return ExportResult(status=404)

    buf = io.BytesIO()

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(
            ndjson_path,
            arcname=os.path.join("experiment", file_name, "testdata.ndjson"),
        )

        for root_dir, _, files in os.walk(cap_dir):
            for fn in files:
                full_path = os.path.join(root_dir, fn)
                rel_path = os.path.relpath(full_path, ROOT)
                z.write(full_path, arcname=rel_path)

    return ExportResult(
        status=200,
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{file_name}.zip"',
        },
    )
    
def parse_predict_body(body: Dict[str, Any]) -> Dict[str, Any]:
    if "pred_bps" not in body:
        raise ValueError("Missing required field: pred_bps")

    pred_bps = float(body["pred_bps"])

    profile = body.get("profile")
    originFolderName = body.get("originFolderName")
    runFolderName = body.get("runFolderName")
    network = body.get("networkName")
    render_ms = body.get("renderMs")
    frameid = body.get("frameid")
    beginTime = body.get("beginTime")
    endTime = body.get("endTime")
    
    return {
        "frameid": frameid,
        "beginTime": beginTime,
        "endTime":endTime,
        "pred_bps": pred_bps,
        "profile": profile,
        "originFolderName": originFolderName,
        "runFolderName": runFolderName,
        "network": network,
        "render_ms": render_ms,
        "raw": body,  # keep original for logging if you want
    }
    


def get_current_kbps(dev: str = "wlp82s0") -> float | None:
    try:
        out = subprocess.run(["tc", "class", "show", "dev", dev],
                             capture_output=True, text=True, check=False)
        text = out.stdout.strip() or out.stderr.strip()
        match = re.search(r"rate\s+([\d.]+)\s*Kbit", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    except Exception as e:
        logger.warning(
            "[tc] failed to read tc status on dev=%s: %s",
            dev, e
        )

    return None


def now_ms(): 
    return int(time.time() * 1000)

async def metrics_predict_logic(body: Dict[str, Any]) -> HandlerResult:
    try:
        parsed = parse_predict_body(body)
    except (ValueError, TypeError) as e:
        return HandlerResult(status=400, text=f"Invalid JSON: {e}")


    try:
        tc_status = get_current_kbps(parsed["network"]) #Add to file for local testing
    except Exception as e:
        return HandlerResult(status=500, text=f"Failed to read tc status: {e}")

    rec = {
        "frameid": parsed["frameid"],
        "beginTime": parsed["beginTime"],
        "endTime": parsed["endTime"],
        "pred_bps": parsed["pred_bps"],
        "profile": parsed["profile"],
        "renderMs": parsed["render_ms"],
    }

    experimentFolder = os.path.join(EXPERIMENTS_DIR, parsed["originFolderName"])
    os.makedirs(experimentFolder, exist_ok=True)
    
    runFolder = os.path.join(experimentFolder, parsed["runFolderName"])
    os.makedirs(runFolder, exist_ok=True)

    with open(os.path.join(runFolder, "testdata.ndjson"), "a", buffering=1) as f:
        f.write(json.dumps(rec) + "\n")

    logger.info("Request with data: %s", parsed["raw"])

    return HandlerResult(
        status=200,
        payload={"ok": True, "file": parsed["originFolderName"]},
    )

async def save_movement(body: Dict[str, Any]) -> HandlerResult:
    frameid = body.get("frameid")
    originFolderName = body.get("originFolderName")
    runFolderName = body.get("runFolderName")
    modelId = body.get("modelId")
    angle = body.get("angle")
    elevation = body.get("elevation")
    x = body.get("x")
    y = body.get("y")
    z = body.get("z")
    fx = body.get("fx")
    fy = body.get("fy")
    cx = body.get("cx")
    cy = body.get("cy")
    width = body.get("width")
    height = body.get("height")
    profile = body.get("profile")


    movement = {
        "frameid": frameid,
        "modelId": modelId,
        "angle": angle,
        "elevation": elevation,
        "x": x,
        "y": y,
        "z": z,
        "fx": fx,
        "fy": fy,
        "cx": cx,
        "cy": cy,
        "width":width,
        "height": height,
        "profile": profile   
    }
    
    print(movement)

    experimentFolder = os.path.join(EXPERIMENTS_DIR, originFolderName)
    os.makedirs(experimentFolder, exist_ok=True)
    
    runFolder = os.path.join(experimentFolder, runFolderName)
    os.makedirs(runFolder, exist_ok=True)
    
    

    with open(os.path.join(runFolder, "movements.ndjson"), "a", buffering=1) as f:
        f.write(json.dumps(movement) + "\n")

    return HandlerResult(
        status=200,
        payload={"ok": True, "file": movement},
    )