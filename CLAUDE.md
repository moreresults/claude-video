# claude-video

This is a video processing and skill development project.

## Git Worktrees

**Do NOT create git worktrees for this project.** Never invoke the `using-git-worktrees` skill here. All work runs directly on the main repo at `/Users/jameswatson/Dropbox/GIT/claude-video`.

## Output Files

When invoking `/watch` in this repo, **always pass `--save-dir outputs/`** (relative to the repo root: `/Users/jameswatson/Dropbox/GIT/claude-video/outputs/`). The script then allocates a `UCID-NNNN YYYY-MM-DD Short Title/` subfolder automatically.

Do **not** run `/watch` with the default tmp-dir behaviour and then `mv` / `cp` the result into `outputs/` under a hand-written name — the script's UCID/sanitisation logic exists specifically to prevent that, and bypassing it has historically left folders with parentheses, ampersands, smart quotes, and other chars that break the markdown-to-apple PDF/DOCX pipeline.

Do not resolve paths using the system prompt's working directory display — use the actual repo path above.

## Never bypass the `/watch` Skill

**Do not call `scripts/watch.py` directly via Bash, even for batch runs.** The Python script only executes steps 0–4 of the pipeline (download / frames / transcript). Step 4.5 (humanized business article + `.docx` + `.pdf` render via [markdown-to-apple-deliverable](https://github.com/anthropics/claude-skills)) is implemented in the Skill itself, not the script. Bypassing the Skill silently skips Step 4.5 — the UCID folder ends up with `transcript.md` but no `business-article.{md,docx,pdf}`.

For batch processing of multiple URLs, invoke the `/watch` Skill per URL (one per turn or via subagents). The per-UCID `business-article.REQUIRED` sentinel file is the on-disk check: any UCID folder containing that file has not yet had Step 4.5 completed. To find all missing articles across the repo:

```bash
find /Users/jameswatson/Dropbox/GIT/claude-video/outputs -name 'business-article.REQUIRED'
```

Empty output means every UCID folder is complete.
