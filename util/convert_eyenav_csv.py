#!/usr/bin/env python3
"""
Convert EyeNavGS CSV traces into playback JSON for GaussianAdaptiveStreamer.

Input CSV columns (required):
ViewIndex,FOV1,FOV2,FOV3,FOV4,PositionX,PositionY,PositionZ,
QuaternionX,QuaternionY,QuaternionZ,QuaternionW,
GazeQX,GazeQY,GazeQZ,GazeQW,GazePosX,GazePosY,GazePosZ,timestep

Output JSON events contain keys expected by playback:
tMs,durationMs,angle,elevation,x,y,z,fx,fy,cx,cy,width,height,profile
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Iterable


REQUIRED_CANONICAL_COLUMNS = {
    "ViewIndex",
    "PositionX",
    "PositionY",
    "PositionZ",
    "QuaternionX",
    "QuaternionY",
    "QuaternionZ",
    "QuaternionW",
    "GazeQX",
    "GazeQY",
    "GazeQZ",
    "GazeQW",
    "GazePosX",
    "GazePosY",
    "GazePosZ",
    "timestep",
}


ALIASES: dict[str, tuple[str, ...]] = {
    "ViewIndex": ("ViewIndex",),
    "PositionX": ("PositionX",),
    "PositionY": ("PositionY",),
    "PositionZ": ("PositionZ",),
    "QuaternionX": ("QuaternionX",),
    "QuaternionY": ("QuaternionY",),
    "QuaternionZ": ("QuaternionZ",),
    "QuaternionW": ("QuaternionW",),
    "GazeQX": ("GazeQX",),
    "GazeQY": ("GazeQY",),
    "GazeQZ": ("GazeQZ",),
    "GazeQW": ("GazeQW",),
    "GazePosX": ("GazePosX",),
    "GazePosY": ("GazePosY",),
    "GazePosZ": ("GazePosZ",),
    "timestep": ("timestep", "Timestamp", "timestamp"),
}


def _build_column_map(fieldnames: list[str] | None) -> dict[str, str]:
    cols = set(fieldnames or [])
    col_map: dict[str, str] = {}
    for canonical, candidates in ALIASES.items():
        for cand in candidates:
            if cand in cols:
                col_map[canonical] = cand
                break

    missing = sorted(REQUIRED_CANONICAL_COLUMNS - set(col_map.keys()))
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    return col_map


def _f(row: dict[str, str], col_map: dict[str, str], key: str) -> float:
    return float(row[col_map[key]])


def _i(row: dict[str, str], col_map: dict[str, str], key: str) -> int:
    return int(float(row[col_map[key]]))


def _normalize_quat(qx: float, qy: float, qz: float, qw: float) -> tuple[float, float, float, float]:
    n = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if n <= 1e-12:
        return 0.0, 0.0, 0.0, 1.0
    return qx / n, qy / n, qz / n, qw / n


def _rotate_vec_by_quat(
    qx: float, qy: float, qz: float, qw: float, vx: float, vy: float, vz: float
) -> tuple[float, float, float]:
    # v' = v + 2*w*(q_xyz x v) + 2*(q_xyz x (q_xyz x v))
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)

    c2x = qy * tz - qz * ty
    c2y = qz * tx - qx * tz
    c2z = qx * ty - qy * tx

    rx = vx + qw * tx + c2x
    ry = vy + qw * ty + c2y
    rz = vz + qw * tz + c2z
    return rx, ry, rz


def _yaw_pitch_from_quat(
    qx: float,
    qy: float,
    qz: float,
    qw: float,
    forward_axis: str,
) -> tuple[float, float]:
    qx, qy, qz, qw = _normalize_quat(qx, qy, qz, qw)

    base = {
        "negz": (0.0, 0.0, -1.0),
        "posz": (0.0, 0.0, 1.0),
        "negx": (-1.0, 0.0, 0.0),
        "posx": (1.0, 0.0, 0.0),
    }[forward_axis]

    dx, dy, dz = _rotate_vec_by_quat(qx, qy, qz, qw, *base)
    norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    if norm <= 1e-12:
        return 180.0, 0.0
    dx, dy, dz = dx / norm, dy / norm, dz / norm

    angle = (math.degrees(math.atan2(dx, -dz)) + 360.0) % 360.0
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, dy))))
    return angle, elevation


def _collect_csvs(inp: Path, recursive: bool) -> list[Path]:
    if inp.is_file():
        return [inp]
    if inp.is_dir():
        it: Iterable[Path] = inp.rglob("*.csv") if recursive else inp.glob("*.csv")
        return sorted([p for p in it if p.is_file()])
    raise FileNotFoundError(f"Input not found: {inp}")


def convert_one(
    src_csv: Path,
    out_json: Path,
    view_index: int | None,
    position_source: str,
    orientation_source: str,
    forward_axis: str,
    timestep_scale: float,
    fallback_duration_ms: int,
    pos_scale: float,
    offset_x: float,
    offset_y: float,
    offset_z: float,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    width: int,
    height: int,
    profile: int,
) -> tuple[int, int]:
    with src_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        try:
            col_map = _build_column_map(reader.fieldnames)
        except ValueError as e:
            raise ValueError(f"{src_csv}: {e}") from e

        rows: list[dict[str, str]] = []
        total_rows = 0
        for row in reader:
            total_rows += 1
            if view_index is not None and _i(row, col_map, "ViewIndex") != view_index:
                continue
            rows.append(row)

    if not rows:
        raise ValueError(f"{src_csv}: no rows after filtering")

    ts = [_f(r, col_map, "timestep") * timestep_scale for r in rows]
    t0 = ts[0]

    events: list[dict[str, float | int]] = []
    n = len(rows)
    for idx, row in enumerate(rows):
        if position_source == "position":
            x = _f(row, col_map, "PositionX")
            y = _f(row, col_map, "PositionY")
            z = _f(row, col_map, "PositionZ")
        else:
            x = _f(row, col_map, "GazePosX")
            y = _f(row, col_map, "GazePosY")
            z = _f(row, col_map, "GazePosZ")

        if orientation_source == "camera":
            qx = _f(row, col_map, "QuaternionX")
            qy = _f(row, col_map, "QuaternionY")
            qz = _f(row, col_map, "QuaternionZ")
            qw = _f(row, col_map, "QuaternionW")
        else:
            qx = _f(row, col_map, "GazeQX")
            qy = _f(row, col_map, "GazeQY")
            qz = _f(row, col_map, "GazeQZ")
            qw = _f(row, col_map, "GazeQW")

        angle, elevation = _yaw_pitch_from_quat(qx, qy, qz, qw, forward_axis=forward_axis)

        t_ms = int(round(ts[idx] - t0))
        if idx + 1 < n:
            duration_ms = int(round(max(1.0, ts[idx + 1] - ts[idx])))
        else:
            duration_ms = int(max(1, fallback_duration_ms))

        events.append(
            {
                "tMs": t_ms,
                "durationMs": duration_ms,
                "angle": angle,
                "elevation": elevation,
                "x": x * pos_scale + offset_x,
                "y": y * pos_scale + offset_y,
                "z": z * pos_scale + offset_z,
                "fx": fx,
                "fy": fy,
                "cx": cx,
                "cy": cy,
                "width": width,
                "height": height,
                "profile": profile,
            }
        )

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(events, indent=2), encoding="utf-8")
    return total_rows, len(events)


def main() -> None:
    p = argparse.ArgumentParser(description="Convert EyeNavGS CSV traces to playback JSON")
    p.add_argument("input", type=Path, help="CSV file or folder with CSV files")
    p.add_argument("--output", type=Path, default=None, help="Output .json file (single input) or output folder")
    p.add_argument("--recursive", "-r", action="store_true", help="Recursively scan folders for CSV files")
    p.add_argument("--view-index", type=int, default=0, help="Filter rows by ViewIndex. Use -1 to keep all")
    p.add_argument(
        "--position-source",
        choices=["position", "gaze"],
        default="position",
        help="Use camera position or gaze position",
    )
    p.add_argument(
        "--orientation-source",
        choices=["camera", "gaze"],
        default="camera",
        help="Use camera quaternion or gaze quaternion for angle/elevation",
    )
    p.add_argument(
        "--forward-axis",
        choices=["negz", "posz", "negx", "posx"],
        default="negz",
        help="Forward basis vector before quaternion rotation",
    )
    p.add_argument(
        "--timestep-scale",
        type=float,
        default=1.0,
        help="Multiply timestep by this value before conversion to milliseconds",
    )
    p.add_argument("--fallback-duration-ms", type=int, default=16, help="Duration for final event")
    p.add_argument("--pos-scale", type=float, default=1.0, help="Scale x/y/z positions")
    p.add_argument("--offset-x", type=float, default=0.0, help="Additive x offset")
    p.add_argument("--offset-y", type=float, default=0.0, help="Additive y offset")
    p.add_argument("--offset-z", type=float, default=0.0, help="Additive z offset")
    p.add_argument("--fx", type=float, default=1300.0)
    p.add_argument("--fy", type=float, default=800.0)
    p.add_argument("--cx", type=float, default=400.0)
    p.add_argument("--cy", type=float, default=300.0)
    p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=600)
    p.add_argument("--profile", type=int, default=0)

    args = p.parse_args()
    view_index = None if args.view_index < 0 else args.view_index

    csv_paths = _collect_csvs(args.input, recursive=args.recursive)
    if not csv_paths:
        raise SystemExit("No CSV files found")

    if len(csv_paths) == 1 and args.output and args.output.suffix.lower() == ".json":
        out_paths = [args.output]
    else:
        if args.output is not None:
            out_root = args.output
        elif args.input.is_dir():
            out_root = args.input / "converted_json"
        else:
            out_root = args.input.parent

        if len(csv_paths) == 1 and args.input.is_file() and args.output is None:
            out_paths = [out_root / (csv_paths[0].stem + ".json")]
        else:
            if args.input.is_dir():
                base = args.input
                out_paths = [
                    out_root / p.relative_to(base).with_suffix(".json")
                    for p in csv_paths
                ]
            else:
                out_paths = [out_root / (p.stem + ".json") for p in csv_paths]

    print(f"Found {len(csv_paths)} CSV file(s)")
    converted = 0
    for src, dst in zip(csv_paths, out_paths):
        total_rows, kept_rows = convert_one(
            src_csv=src,
            out_json=dst,
            view_index=view_index,
            position_source=args.position_source,
            orientation_source=args.orientation_source,
            forward_axis=args.forward_axis,
            timestep_scale=args.timestep_scale,
            fallback_duration_ms=args.fallback_duration_ms,
            pos_scale=args.pos_scale,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
            offset_z=args.offset_z,
            fx=args.fx,
            fy=args.fy,
            cx=args.cx,
            cy=args.cy,
            width=args.width,
            height=args.height,
            profile=args.profile,
        )
        converted += 1
        print(f"[ok] {src} -> {dst} (rows: {kept_rows}/{total_rows})")

    print(f"Done. Converted {converted} file(s).")


if __name__ == "__main__":
    main()
