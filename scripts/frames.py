#!/usr/bin/env python3
"""Probe video metadata and extract frames at an auto-scaled fps.

Auto-fps targets a frame budget, not a fixed rate. Token cost scales with frame
count, so budget-by-duration keeps short videos dense and long videos capped.
When a user-specified range is passed, focused-mode budgets denser (they are
zooming in for detail).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


MAX_FPS = 2.0
DEFAULT_HIRES_RESOLUTION = 1600  # newsletter / publication frame width


def _clamp_fps(fps: float, duration_seconds: float, max_frames: int) -> tuple[float, int]:
    fps = min(fps, MAX_FPS)
    target = min(max_frames, max(1, int(round(fps * duration_seconds))))
    return fps, target


def parse_time(value: str | float | int | None) -> float | None:
    """Parse SS, MM:SS, or HH:MM:SS (with optional .ms) into seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    parts = s.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    raise SystemExit(f"Cannot parse time value: {value!r} (expected SS, MM:SS, or HH:MM:SS)")


def format_time(seconds: float) -> str:
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, sec = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def get_metadata(video_path: str) -> dict:
    if shutil.which("ffprobe") is None:
        raise SystemExit("ffprobe is not installed. Install with: brew install ffmpeg")

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(Path(video_path).resolve()),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"ffprobe failed: {result.stderr.strip()}")

    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    fmt = data.get("format", {})
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(fmt.get("duration") or video_stream.get("duration") or 0)
    return {
        "duration_seconds": duration,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "codec": video_stream.get("codec_name"),
        "size_bytes": int(fmt.get("size") or 0),
        "has_audio": audio_stream is not None,
    }


def auto_fps(duration_seconds: float, max_frames: int = 100) -> tuple[float, int]:
    """Pick fps that targets a sensible frame budget for full-video scans."""
    if duration_seconds <= 0:
        return 1.0, 1

    if duration_seconds <= 30:
        target = min(max_frames, max(12, int(round(duration_seconds))))
    elif duration_seconds <= 60:
        target = min(max_frames, 40)
    elif duration_seconds <= 180:  # 3 min
        target = min(max_frames, 60)
    elif duration_seconds <= 600:  # 10 min
        target = min(max_frames, 80)
    else:
        target = max_frames

    return _clamp_fps(target / duration_seconds, duration_seconds, max_frames)


def auto_fps_focus(duration_seconds: float, max_frames: int = 100) -> tuple[float, int]:
    """Denser budget for user-specified ranges — they are zooming in for detail."""
    if duration_seconds <= 0:
        return min(MAX_FPS, 2.0), 2

    if duration_seconds <= 5:
        target = min(max_frames, max(10, int(round(duration_seconds * 6))))
    elif duration_seconds <= 15:
        target = min(max_frames, max(30, int(round(duration_seconds * 4))))
    elif duration_seconds <= 30:
        target = min(max_frames, 60)
    elif duration_seconds <= 60:
        target = min(max_frames, 80)
    elif duration_seconds <= 180:
        target = max_frames
    else:
        target = max_frames

    return _clamp_fps(target / duration_seconds, duration_seconds, max_frames)


def extract(
    video_path: str,
    out_dir: Path,
    fps: float,
    resolution: int = 512,
    hires_resolution: int = DEFAULT_HIRES_RESOLUTION,
    max_frames: int = 100,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    hires_dir: Path | None = None,
) -> list[dict]:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is not installed. Install with: brew install ffmpeg")

    if hires_dir is None:
        hires_dir = out_dir.parent / "hires"

    out_dir.mkdir(parents=True, exist_ok=True)
    hires_dir.mkdir(parents=True, exist_ok=True)
    for existing in out_dir.glob("frame_*.jpg"):
        existing.unlink()
    for existing in hires_dir.glob("frame_*.jpg"):
        existing.unlink()

    lo_pattern = str(out_dir / "frame_%04d.jpg")
    hi_pattern = str(hires_dir / "frame_%04d.jpg")

    # Build the filter graph. trim happens BEFORE fps and split so both
    # outputs are guaranteed to receive identical frames at identical
    # indices. setpts=PTS-STARTPTS resets timestamps to 0 after trim so
    # the downstream fps filter sees a clean 0-based stream.
    #
    # scale='min(W,iw)':-2 caps the output width at W without ever
    # upscaling a smaller source — a 1280px-wide 720p input asked for
    # 1600px hi-res will stay at 1280px rather than balloon to a soft
    # 1600px.
    trim_args = []
    if start_seconds is not None:
        trim_args.append(f"start={start_seconds:.3f}")
    if end_seconds is not None:
        trim_args.append(f"end={end_seconds:.3f}")
    trim_stage = f"trim={':'.join(trim_args)},setpts=PTS-STARTPTS," if trim_args else ""

    filter_graph = (
        f"[0:v]{trim_stage}fps={fps},split=2[lo_src][hi_src];"
        f"[lo_src]scale='min({resolution},iw)':-2[lo];"
        f"[hi_src]scale='min({hires_resolution},iw)':-2[hi]"
    )

    cmd: list[str] = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(Path(video_path).resolve()),
        "-filter_complex", filter_graph,
        "-map", "[lo]", "-frames:v", str(max_frames), "-q:v", "4", lo_pattern,
        "-map", "[hi]", "-frames:v", str(max_frames), "-q:v", "2", hi_pattern,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg frame extraction failed: {result.stderr.strip()}")

    offset = start_seconds or 0.0
    lo_frames = sorted(out_dir.glob("frame_*.jpg"))
    hi_frames = sorted(hires_dir.glob("frame_*.jpg"))

    # Hard invariant: both encoders share one decode pass via split=2 inside
    # the filter graph. If counts diverge, the graph has been altered and
    # the index → moment mapping is no longer trustworthy. Fail loudly.
    if len(lo_frames) != len(hi_frames):
        raise SystemExit(
            f"frame count mismatch: {len(lo_frames)} lo vs {len(hi_frames)} hi — "
            "filter graph altered or ffmpeg behaviour is off"
        )

    return [
        {
            "index": i,
            "timestamp_seconds": round(offset + (i / fps if fps > 0 else 0.0), 2),
            "path": str(lo_p),
            "hires_path": str(hi_p),
        }
        for i, (lo_p, hi_p) in enumerate(zip(lo_frames, hi_frames))
    ]


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "usage: frames.py <video-path> <out-dir> [--fps F] [--resolution W] "
            "[--max-frames N] [--start T] [--end T]",
            file=sys.stderr,
        )
        raise SystemExit(2)

    video = sys.argv[1]
    out = Path(sys.argv[2])
    args = sys.argv[3:]

    fps_override = None
    resolution = 512
    hires_resolution = DEFAULT_HIRES_RESOLUTION
    max_frames = 100
    start_arg = None
    end_arg = None
    i = 0
    while i < len(args):
        if args[i] == "--fps":
            fps_override = float(args[i + 1]); i += 2
        elif args[i] == "--resolution":
            resolution = int(args[i + 1]); i += 2
        elif args[i] == "--hires-resolution":
            hires_resolution = int(args[i + 1]); i += 2
        elif args[i] == "--max-frames":
            max_frames = int(args[i + 1]); i += 2
        elif args[i] == "--start":
            start_arg = args[i + 1]; i += 2
        elif args[i] == "--end":
            end_arg = args[i + 1]; i += 2
        else:
            i += 1

    meta = get_metadata(video)
    start_sec = parse_time(start_arg)
    end_sec = parse_time(end_arg)
    full_duration = meta["duration_seconds"]

    effective_start = start_sec if start_sec is not None else 0.0
    effective_end = end_sec if end_sec is not None else full_duration
    effective_duration = max(0.0, effective_end - effective_start)

    focused = start_sec is not None or end_sec is not None
    if focused:
        fps, target = auto_fps_focus(effective_duration, max_frames=max_frames)
    else:
        fps, target = auto_fps(effective_duration, max_frames=max_frames)
    if fps_override is not None:
        fps = fps_override
        target = max(1, int(round(fps * effective_duration)))

    frames = extract(
        video, out,
        fps=fps,
        resolution=resolution,
        hires_resolution=hires_resolution,
        max_frames=max_frames,
        start_seconds=start_sec,
        end_seconds=end_sec,
    )
    print(json.dumps(
        {"meta": meta, "fps": fps, "target": target, "focused": focused,
         "resolution": resolution, "hires_resolution": hires_resolution,
         "frames": frames},
        indent=2,
    ))
