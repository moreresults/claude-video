#!/usr/bin/env python3
"""One-shot: migrate existing outputs/ folders to the UCID-NNNN format.

For each folder under outputs/:
  1. Reads metadata from download/video.info.json (falls back to the
     existing folder name if the json is missing).
  2. Builds a new name `UCID-NNNN YYYY-MM-DD Short Title` via the
     shared safe_name helpers, with UCIDs allocated in chronological
     order across the whole set.
  3. Rewrites any reference to the old folder name inside the .md files
     (business-article.md and transcript.md) so absolute frame paths
     keep working.
  4. Moves the folder.
  5. Regenerates business-article.docx and business-article.pdf via
     the markdown-to-apple-deliverable skill.

Safe to run multiple times: folders already matching `UCID-NNNN ` are
skipped on subsequent runs.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).parent.resolve()
sys.path.insert(0, str(REPO / "scripts"))

from safe_name import DEFAULT_UCID_PREFIX, UCID_PAD, build_save_dir_name  # noqa: E402

OUTPUTS = REPO / "outputs"
SKILL_DIR = Path.home() / ".claude" / "skills" / "markdown-to-apple-deliverable" / "scripts"
NODE_PATH = subprocess.check_output(["npm", "root", "-g"], text=True).strip()


def load_info(folder: Path) -> dict:
    """Pull title/uploader/upload_date from the saved yt-dlp info json."""
    info_json = folder / "download" / "video.info.json"
    if info_json.exists():
        raw = json.loads(info_json.read_text(encoding="utf-8"))
        return {
            "title": raw.get("title"),
            "uploader": raw.get("uploader") or raw.get("channel"),
            "upload_date": raw.get("upload_date"),
        }
    # Fallback for the rare folder without info.json: parse the name.
    name = folder.name
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2}) (.+)$", name)
    if not m:
        return {"title": name}
    yyyy, mm, dd, rest = m.groups()
    if " - " in rest:
        uploader, title = rest.split(" - ", 1)
    else:
        uploader, title = "", rest
    return {"title": title, "uploader": uploader, "upload_date": f"{yyyy}{mm}{dd}"}


def rewrite_md_refs(folder: Path, old_name: str, new_name: str) -> int:
    """Replace old folder-name (literal AND URL-encoded) with new in .md files.

    Some markdown was written with `quote()`-style absolute paths
    (`%20`, `%28`, `%29`) — those wouldn't match the literal folder name,
    so we replace both forms.
    """
    forms = {old_name: new_name, quote(old_name): new_name}
    total = 0
    for md in folder.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        new_text = text
        for old, new in forms.items():
            if old in new_text:
                total += new_text.count(old)
                new_text = new_text.replace(old, new)
        if new_text != text:
            md.write_text(new_text, encoding="utf-8")
    return total


def regenerate_outputs(folder: Path) -> None:
    md = folder / "business-article.md"
    if not md.exists():
        return
    env = {**os.environ, "NODE_PATH": NODE_PATH}
    for script in ("md_to_docx.js", "md_to_pdf.js"):
        subprocess.run(
            ["node", str(SKILL_DIR / script), str(md), "--out", str(folder)],
            check=True, env=env,
        )


_UCID_RE = re.compile(rf"^{re.escape(DEFAULT_UCID_PREFIX)}-\d+\b")


def main() -> int:
    folders = sorted(
        [p for p in OUTPUTS.iterdir() if p.is_dir() and not _UCID_RE.match(p.name)],
        key=lambda p: p.name[:10],
    )
    if not folders:
        print("Nothing to migrate.")
        return 0

    # Allocate UCIDs continuing from any already-migrated folder.
    existing = [p for p in OUTPUTS.iterdir() if _UCID_RE.match(p.name)]
    used = []
    for p in existing:
        m = re.match(rf"^{re.escape(DEFAULT_UCID_PREFIX)}-(\d+)", p.name)
        if m:
            used.append(int(m.group(1)))
    start = (max(used) + 1) if used else 1

    plan: list[tuple[Path, str]] = []
    for i, folder in enumerate(folders):
        ucid = f"{DEFAULT_UCID_PREFIX}-{start + i:0{UCID_PAD}d}"
        new_name = build_save_dir_name(load_info(folder), ucid=ucid)
        plan.append((folder, new_name))

    print(f"Migrating {len(plan)} folder(s):")
    for old, new in plan:
        print(f"  {old.name}")
        print(f"  →  {new}\n")

    for old, new in plan:
        new_path = old.parent / new
        if new_path.exists():
            print(f"SKIP (target exists): {new}")
            continue
        n = rewrite_md_refs(old, old.name, new)
        shutil.move(str(old), str(new_path))
        regenerate_outputs(new_path)
        suffix = f" (rewrote {n} ref{'s' if n != 1 else ''})" if n else ""
        print(f"OK  {new}{suffix}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
