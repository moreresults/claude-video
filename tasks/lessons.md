# Lessons learned — `/watch` skill rebuild

**Date:** 2026-05-18
**Scope:** `/watch` skill, `markdown-to-apple-deliverable` skill, `outputs/` folder convention
**Repo:** `/Users/jameswatson/Dropbox/GIT/claude-video`

---

## 1. The image regex broke on paths containing `)`

**Symptom.** Two folders' PDFs and DOCX (`Brad AI`, `Kyle Balmer`) silently rendered with zero images. The `business-article.md` was unchanged; the toolchain was the same as for the other folders that worked.

**Root cause.** The shared markdown parser in [`markdown-to-apple-deliverable/scripts/_parser.js`](file://~/.claude/skills/markdown-to-apple-deliverable/scripts/_parser.js) used a non-greedy URL group:

```js
const im = line.match(/^!\[([^\]]*)\]\(([^)]+)\)\s*$/);
```

`[^)]+` stops at the first `)`. For an image whose absolute path contained `(Here's How)` or `(Explained in 20 minutes)`, the regex never matched and the line silently became a paragraph. No error, no warning — the image was just absent from the rendered output.

**Fix.** Made the URL group greedy and anchored on the *last* `)` on the line:

```js
const im = line.match(/^!\[([^\]]*)\]\((.+)\)\s*$/);
```

Plus a "Known gotchas (don't reintroduce)" section in `SKILL.md` so a future edit doesn't tighten the regex back.

**Verification.** `pdfimages -list` on every output. All 13 folders show `md count == docx count == pdf count` for embedded images.

---

## 2. Folder names accumulated chars that break the toolchain

**Symptom.** Folder names like `2026-04-29 Brad AI & Automation - My Claude Code Can INSTANTLY Watch Any Video (Here's How)/` contained parentheses, ampersands, smart quotes, apostrophes, exclamation marks — all chars that have a history of breaking *something*:

- `(` `)` — broke the image regex (issue 1).
- `#` `?` `&` — Chrome's `file://` URL handling reads these as URL syntax; `md_to_pdf.js` works around it for the intermediate HTML path but the surrounding folder name still hurts when passed to other tools.
- `'` `'` `'` `"` `"` — apostrophes break unquoted shell expansion; smart quotes render inconsistently.
- `!` `;` `$` `` ` `` `[]{}=` — shell metacharacters.
- `<>:"/\|?*` — POSIX/Windows path-unsafe set.

**Root cause.** Claude was constructing folder names freehand (from yt-dlp metadata) without any sanitisation pass. The `--save-dir` flag documented in `REFERENCE.md` was never actually implemented in the script.

**Fix.** New module [`scripts/safe_name.py`](scripts/safe_name.py):

- `sanitize_segment()` — restricts to `[A-Za-z0-9 _.,-]`, normalises smart quotes / en-em dashes / ellipsis, collapses whitespace, trims punctuation, caps length.
- `build_save_dir_name(info, ucid=...)` — composes the folder name with each segment sanitised independently.
- `next_ucid(save_dir, prefix)` — scans existing `<PREFIX>-NNNN*` folders and returns `max+1` zero-padded.

Wired into `watch.py` with new `--save-dir` and `--ucid-prefix` flags. The script downloads into a staging tmp dir, computes the sanitised name, and `shutil.move`s the whole dir into place (atomic on the same FS) — Claude never has the chance to inject a freehand name.

**Verification.** [`scripts/test_save_dir.sh`](scripts/test_save_dir.sh) — generates a fake video named `demo with (parens) & ampersand!.mp4`, runs the full pipeline, asserts the output folder is `UCID-NNNN YYYY-MM-DD demo with parens ampersand.mp4` (parens/ampersand/exclam stripped).

---

## 3. Folder names were also unreadably long

**Symptom.** Folder names like `2026-04-27 Nick Puru - Nick Puru - The internet says AI is here to replace your team. I sat on 50 sales/` truncated awkwardly in `ls`, broke chronological visual scans, and made cross-referencing them in conversation slow.

**Fix.** UCID format: `UCID-NNNN YYYY-MM-DD Short Title`. Title truncated to ~40 chars at a word boundary. The full title is preserved inside `download/video.info.json`, `transcript.md`, and `business-article.md`, so nothing is lost.

Migration script `migrate_to_ucid.py` (one-shot) renamed all 13 existing folders to UCID-0001…UCID-0013 in chronological order, rewrote absolute frame paths inside `business-article.md` (both literal and URL-encoded forms), and regenerated DOCX + PDF for each. Idempotent — re-runs are no-ops once everything is migrated.

---

## 4. The big one — repo SKILL.md is **not** the SKILL.md Claude loads

**This is the most important lesson of the session.** Hours of edits had effectively zero impact on `/watch` behaviour, and we only found out by directly inspecting what the `Skill` tool actually returned.

**Symptom.** After updating `SKILL.md` in the repo to mandate `--save-dir` and the UCID format, two consecutive `/watch` runs still produced old-format folder names. "Restart Claude" didn't fix it.

**Root cause.** Claude Desktop installs skills into a **per-session cache** at:

```
~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/<session-id>/<sub-id>/skills/watch/
```

This cache is a *snapshot* of the skill at install time. Editing the repo at `~/Dropbox/GIT/claude-video/` does not propagate to the cache. Every `/watch` invocation was loading the older cached `SKILL.md` and the older cached `watch.py` — neither of which had any of my changes.

The skill description in the cached SKILL.md was identical to the repo's, which is why nothing seemed obviously wrong — but the body had drifted by ~50 lines of new logic (UCID, sanitisation, decision rule, `--hires-resolution`).

**Diagnostic move that found it.** Invoking the `watch` skill via the `Skill` tool and reading the *actual loaded text*. The loaded SKILL.md started with `Base directory for this skill: /Users/jameswatson/Library/Application Support/Claude/...` — the moment that path didn't match the repo path, the disconnect was obvious.

**Fix (immediate).** `cp` the four edited files from the repo into the cache:

```
SKILL.md
scripts/watch.py
scripts/download.py
scripts/safe_name.py   (new)
scripts/frames.py
```

**Fix (durable).** Two options, ordered by robustness:

1. **Symlink the cache into the repo** (current session only):
   ```bash
   CACHE='~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/<sid>/<sub>/skills/watch'
   rm -rf "$CACHE/scripts" && ln -s ~/Dropbox/GIT/claude-video/scripts "$CACHE/scripts"
   ln -sf ~/Dropbox/GIT/claude-video/SKILL.md "$CACHE/SKILL.md"
   ```
   Survives within the session. A new session may regenerate the cache from elsewhere and replace the symlinks — re-run when that happens.

2. **Push to the upstream source.** The skill's `homepage:` is `https://github.com/bradautomates/claude-video`. If Claude Desktop pulls from that repo on plugin install, the only way to make changes permanent across reinstalls is to push them upstream and bump the plugin version.

---

## Process lessons (don't repeat)

1. **For any "the skill I edited isn't behaving" debugging — read what the Skill tool actually loaded, not what's on disk in the repo.** They may diverge. The disconnect cost the most time in this session by a wide margin.

2. **A documented flag is not an implemented flag.** `--save-dir` was in `REFERENCE.md` for days before it had code behind it. When a flag isn't doing what the docs claim, *grep the script for the flag name* before debugging from the user end.

3. **Silent failures are the worst kind.** The image regex didn't error, it just produced documents with missing images. The folder-naming bug didn't error, it just made downstream tools fail later. Add `pdfimages -list`-style assertions to the test suite so silent regressions surface immediately.

4. **`pdfimages` counts include 1-channel alpha masks for rounded-corner images.** Filter on `$6!="gray"` when scripting verification, or counts inflate to 2× for any image rendered with `border-radius`.

5. **When sanitising, strip rather than substitute.** Replacing `&` with `and` or `(` with `-` produces names that look fine to a human but still need different escaping in different contexts. Keep only `[A-Za-z0-9 _.,-]` and trust that the full title lives in metadata.

6. **The user's CLAUDE.md is not the LLM's CLAUDE.md.** This repo's `CLAUDE.md` said "use `--save-dir outputs/`" — but the skill being loaded (the cached one) wasn't aware. Project memory only helps Claude make the right call; it doesn't fix code that ignores its arguments.
