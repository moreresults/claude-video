#!/usr/bin/env python3
"""Filesystem-safe folder naming for /watch output dirs.

Produces names of the form `YYYY-MM-DD Uploader - Title`, stripped of
characters that have caused downstream tooling failures:

- `(` `)` — broke an earlier image-path regex in the markdown-to-apple
  deliverable parser (greedy fix is in place, but defense-in-depth).
- `#` `?` `&` — Chrome's `file://` URL handling treats these as URL
  syntax, so they can corrupt PDF rendering when a path is embedded.
- ``< > : " / \\ | ? *`` — POSIX/Windows path-unsafe set.
- `'` `'` `'` `"` `"` — apostrophes and smart quotes; the former breaks
  unquoted shell expansion, the latter renders inconsistently.
- `!` ``  `` `$` `;` `[` `]` `{` `}` `=` — shell metacharacters.

The result is restricted to alphanumerics, spaces, hyphens, dots,
commas, and underscores. Whitespace is collapsed and the segment is
trimmed of leading/trailing punctuation.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path


# Smart-quote / dash / ellipsis normalisation before stripping.
_TRANSLATE = str.maketrans({
    "‘": "",   # '
    "’": "",   # '
    "‚": "",   # ‚
    "‛": "",   # ‛
    "“": "",   # "
    "”": "",   # "
    "„": "",   # „
    "–": "-",  # – en dash
    "—": "-",  # — em dash
    "…": "",   # … ellipsis
    " ": " ",  # nbsp
})

# Keep alphanumerics plus a small punctuation set known to be portable
# across macOS/Linux/Windows and benign to every tool in this pipeline.
_KEEP = re.compile(r"[^A-Za-z0-9 _.,\-]+")
_WS = re.compile(r"\s+")
# Strip leading/trailing chars that look ugly or trip directory listings.
_TRIM = " .-_,"


def sanitize_segment(s: str | None, max_len: int = 80) -> str:
    """Return a single path segment safe for any filesystem and our tools.

    Empty / None input returns "". The result will never contain a path
    separator and will be at most `max_len` chars long.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = s.translate(_TRANSLATE)
    s = _KEEP.sub("", s)
    s = _WS.sub(" ", s).strip(_TRIM)
    if len(s) > max_len:
        s = s[:max_len].rstrip(_TRIM)
    return s


def _format_date(upload_date: str | None) -> str:
    """yt-dlp emits `upload_date` as `YYYYMMDD`. Reformat to `YYYY-MM-DD`.

    Falls back to today's local date if the field is missing or malformed.
    """
    if upload_date and len(upload_date) == 8 and upload_date.isdigit():
        return f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    return datetime.now().strftime("%Y-%m-%d")


DEFAULT_UCID_PREFIX = "UCID"
UCID_PAD = 4
SHORT_TITLE_MAX = 40


def _short_title(title: str | None) -> str:
    """Sanitize the title and truncate it at a word boundary.

    Result is at most `SHORT_TITLE_MAX` chars and never ends mid-word
    when the input is longer than the cap. Falls back to "video" if
    the sanitized title is empty.
    """
    cleaned = sanitize_segment(title, max_len=SHORT_TITLE_MAX * 2)
    if not cleaned:
        return "video"
    if len(cleaned) <= SHORT_TITLE_MAX:
        return cleaned
    cut = cleaned[:SHORT_TITLE_MAX]
    # Trim back to the last full word so we don't end mid-token.
    sp = cut.rfind(" ")
    if sp >= SHORT_TITLE_MAX // 2:
        cut = cut[:sp]
    return cut.rstrip(_TRIM)


_UCID_RE_TMPL = r"^{prefix}-(\d+)\b"


def next_ucid(save_dir: Path | str, prefix: str = DEFAULT_UCID_PREFIX) -> str:
    """Return the next free UCID under `save_dir` for the given prefix.

    Scans immediate subdirectories matching `<prefix>-NNNN…` and picks
    `max(N) + 1`. Returns `<prefix>-0001` when no matching folder
    exists yet (or when `save_dir` doesn't exist).
    """
    base = Path(save_dir)
    pattern = re.compile(_UCID_RE_TMPL.format(prefix=re.escape(prefix)))
    highest = 0
    if base.is_dir():
        for entry in base.iterdir():
            if not entry.is_dir():
                continue
            m = pattern.match(entry.name)
            if m:
                try:
                    n = int(m.group(1))
                except ValueError:
                    continue
                highest = max(highest, n)
    return f"{prefix}-{highest + 1:0{UCID_PAD}d}"


def build_save_dir_name(info: dict | None, ucid: str | None = None) -> str:
    """Build the folder name for one piece of content.

    With a `ucid` (e.g. `UCID-0001`) the name is
    `UCID YYYY-MM-DD ShortTitle`. Without one, falls back to the legacy
    `YYYY-MM-DD Uploader - Title` form for callers that haven't opted
    into UCIDs. Each segment is sanitized independently.
    """
    info = info or {}
    date = _format_date(info.get("upload_date"))
    if ucid:
        return f"{ucid} {date} {_short_title(info.get('title'))}"
    uploader = sanitize_segment(info.get("uploader"))
    title = sanitize_segment(info.get("title")) or "video"
    if uploader:
        return f"{date} {uploader} - {title}"
    return f"{date} {title}"


if __name__ == "__main__":
    # Smoke check — run `python3 safe_name.py` to eyeball the output.
    samples = [
        {"upload_date": "20260429", "uploader": "Brad AI & Automation",
         "title": "My Claude Code Can INSTANTLY Watch Any Video (Here's How)"},
        {"upload_date": "20260514", "uploader": "Simon Scrapes",
         "title": "Skill Chaining in Claude OS is INSANE (Don’t Fall Behind!)"},
        {"uploader": None, "title": "local-file.mp4"},
        {"upload_date": "bogus", "uploader": "Foo/Bar", "title": "A?B*C:D"},
    ]
    for i, s in enumerate(samples, 1):
        ucid = f"{DEFAULT_UCID_PREFIX}-{i:04d}"
        print(f"{ucid:<12s}", build_save_dir_name(s, ucid))
