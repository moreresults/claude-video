# /watch — Quick Reference

## Basic syntax

```
/watch <url-or-path> [--save-dir /path] [question]
```

## Saving output

Pass `--save-dir` to keep all assets in a named folder. The folder name is built automatically from the video metadata:

```
YYYY-MM-DD Channel Name - Video Title
```

```
/watch https://youtu.be/abc --save-dir ~/Videos/watched summarize this
```

→ creates `~/Videos/watched/2026-05-16 Simon Scrapes - Every Claude Code Memory System Compared/`

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
| `--save-dir DIR` | — | Base dir; auto-names subfolder from metadata |
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
