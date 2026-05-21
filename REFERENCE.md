# /watch — Quick Reference

## Basic syntax

```
/watch <url-or-path> [--save-dir /path] [question]
```

## Saving output

Pass `--save-dir` to keep all assets in a named folder. The folder name is auto-generated as:

```
UCID YYYY-MM-DD Short Title
```

- **UCID** — auto-allocated unique content ID, e.g. `UCID-0001`. The script scans `--save-dir` for existing `UCID-NNNN*` subfolders, picks the highest `N`, and increments. Override the prefix with `--ucid-prefix XYZ` if you want a different namespace (each prefix has its own counter).
- **YYYY-MM-DD** — the video's publish date from yt-dlp metadata (`upload_date`), falling back to today's date.
- **Short Title** — sanitised and truncated to ~40 chars at a word boundary. Parentheses, ampersands, smart quotes, apostrophes, exclamation marks, shell metacharacters, and any chars unsafe across POSIX/Windows filesystems are stripped. This is deliberate: earlier output folders that contained these characters silently broke the markdown-to-apple PDF/DOCX pipeline (the image-path regex misparses on `)`, and Chrome's `file://` parsing misparses on `&` / `#` / `?`).

```
/watch https://youtu.be/abc --save-dir outputs/ summarize this
```

→ creates `outputs/UCID-0014 2026-05-16 Every Claude Code Memory System/` (or whatever the next UCID is).

Example sanitisation:

|raw metadata|folder name|
|-|-|
|`Brad AI & Automation` / `My Claude Code Can INSTANTLY Watch Any Video (Here's How)`|`UCID-0001 2026-04-29 My Claude Code Can INSTANTLY Watch Any`|
|`Simon Scrapes` / `Skill Chaining in Claude OS is INSANE (Don't Fall Behind!)`|`UCID-0002 2026-05-14 Skill Chaining in Claude OS is INSANE`|

The rules live in `scripts/safe_name.py`. If the target subfolder already exists, the script refuses to overwrite — remove the old folder or pick a different `--save-dir`. The full untruncated title is preserved inside `download/video.info.json` and the generated `transcript.md`/`business-article.md`, so nothing is lost.

If you omit `--save-dir`, Claude will ask you where to save before running. Choose a path or pick "skip" to use a temp dir (cleaned up after).

Contents of the saved folder:

```
download/
  video.mp4
  video.info.json
  video.en.vtt        ← captions if available
frames/
  frame_0001.jpg      ← t=00:00
  frame_0002.jpg      ← t=00:05
  …
audio.mp3             ← only if Whisper was used
```

## Watching a specific section

Use `--start` / `--end` to zoom in. Frame rate is denser in focused mode.

```
/watch https://youtu.be/abc --start 2:15 --end 2:45 what's on screen?
/watch video.mp4 --start 50 --end 60
/watch "$URL" --start 1:12:00         # from 1h12m to end
```

## Common patterns

| Goal | Command |
|-|-|
| Summarize a video | `/watch <url> summarize this` |
| Analyze a hook / intro | `/watch <url> --end 0:30 break down this hook` |
| Debug a screen recording | `/watch bug.mov when does the UI break?` |
| Extract slides / text | `/watch <url> --resolution 1024 list the slide titles` |
| Save without watching | `/watch <url> --save-dir ~/Videos` |

## All flags

| Flag | Default | Purpose |
|-|-|-|
| `--save-dir DIR` | — | Base dir; auto-names subfolder `UCID YYYY-MM-DD Short Title` |
| `--ucid-prefix XYZ` | `UCID` | Override the UCID prefix; only used with `--save-dir` |
| `--out-dir DIR` | temp | Use this exact directory (no naming logic) |
| `--start T` | — | Range start (`SS`, `MM:SS`, or `HH:MM:SS`) |
| `--end T` | — | Range end |
| `--max-frames N` | 80 | Cap frame count (hard max 100) |
| `--resolution W` | 512 | Frame width in px; use 1024 for on-screen text |
| `--fps F` | auto | Override fps (capped at 2) |
| `--whisper groq\|openai` | auto | Force a Whisper backend |
| `--no-whisper` | — | Frames only; skip transcription |

## Frame budget

| Duration | Frames | Notes |
|-|-|-|
| ≤30 s | ~30 | Dense |
| 30 s – 1 min | ~40 | Dense |
| 1 – 3 min | ~60 | Comfortable |
| 3 – 10 min | ~80 | Sparse |
| > 10 min | 100 | Warning printed — prefer `--start`/`--end` |

## Transcript sources

1. **Native captions** — pulled free via yt-dlp (most YouTube, some Vimeo/TikTok)
2. **Whisper (Groq)** — fallback when no captions; `whisper-large-v3`, fast and cheap
3. **Whisper (OpenAI)** — second fallback; `whisper-1`

Keys live in `~/.config/watch/.env`. Run `python3 <skill-dir>/scripts/setup.py` to configure.

## Limits

- Best accuracy under 10 min; past that use `--start`/`--end` on the relevant section
- Whisper upload cap: ~25 MB (≈50 min of mono audio)
- Public URLs and local files only — no login-required platforms
