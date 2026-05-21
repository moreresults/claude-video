# Skill Build Infrastructure — v1.3

> Uses `/watch` as the worked example throughout.

---

## The persistence problem

When you update a skill and it doesn't stick, one of four things happened:

1. **You edited the wrong copy.** There are multiple copies of the skill on disk; Claude loaded a different one.
2. **The bundle wasn't rebuilt.** claude.ai loads a ZIP archive, not raw files. Editing the source repo does nothing until you rebuild and re-upload.
3. **Plugin version wasn't bumped.** If `plugin.json` has a `version` field and you didn't increment it, `/plugin update` will not install the new code — Claude Code uses the version string as the update key. If `version` is omitted from `plugin.json`, Claude Code falls back to the git commit SHA, so every commit is treated as a new version. This is the most silent failure mode.
4. **Claude Code cached the old content.** On macOS, Claude Code as a GUI app does not source `~/.zshrc`, so `CLAUDE_SKILL_DIR` set in the shell profile is invisible to it. The skill path resolves to an old location.

Fixing this requires knowing the exact path each surface loads from, and a deterministic process to update each one.

---

## Surface map

| Surface | Where SKILL.md loads from | How SKILL.md gets there |
|-|-|-|
| **Claude Code — local skill** | `~/.claude/skills/watch/SKILL.md` (user-level) or `.claude/skills/watch/SKILL.md` (project-level) | `git clone` or manual copy |
| **Claude Code — plugin** | `skills/watch/SKILL.md` inside the plugin root; resolved via `${CLAUDE_PLUGIN_ROOT}` | Marketplace install, or `claude --plugin-dir` for local dev |
| **claude.ai (web)** | Unpacked from ZIP archive at upload time | `build-skill.sh` → upload via Customize → Skills |
| **Codex** | `~/.codex/skills/watch/SKILL.md` | `git clone` into `~/.codex/skills/watch` |

The `CLAUDE_SKILL_DIR` environment variable is the local-skill convention. For plugin-packaged skills, the correct variable is `${CLAUDE_PLUGIN_ROOT}` (provided by Claude Code at runtime) — scripts must reference it instead of a manually exported env var.

---

## Skills vs plugins — when to use which

| Situation | Use |
|-|-|
| Personal/project-specific workflow, one machine | Local skill (`~/.claude/skills/` or `.claude/skills/`) |
| Private cloud access across devices | Uploaded custom skill (Customize → Skills, private to your account) |
| Multiple bundled skills + hooks + scripts + versioned releases | Plugin |
| Controlled team/org distribution | Private org plugin marketplace |
| Public/community distribution | Public marketplace plugin |

**For this project now:** keep as skills. Introduce plugins only when one of these becomes true: you need one-click install/update across many machines; you want to bundle several skills plus hooks/scripts together; you need controlled team distribution; you need namespacing across `/video:watch`, `/video:article`, etc.

### Current recommendation for `/watch`

Use local/project skills as the source-of-truth workflow. Do not package `/watch` as a plugin until:

- `/watch` and `/video-to-business-article` are split and their handoff contract is stable
- Version consistency checks are automated
- Private marketplace distribution is actually needed

### Privacy model

```
Personal uploaded skill on claude.ai  = private to your account by default
Shared skill                           = visible only to people you explicitly share with
Org plugin marketplace                 = visible per admin settings (can be restricted)
Public/community plugin                = public
```

Org marketplace repos synced from GitHub must be private or internal — not public.

### What belongs in a distributable skill/plugin

**Safe to include:** instructions, scripts, validators, templates, style rules you are comfortable distributing.

**Never include:** API keys, client secrets, private transcripts, credentials, Dropbox-only private data, personal filesystem paths (unless the skill is explicitly local-only).

---

## Canonical source

There is one source of truth for the skill:

```
~/path/to/moreresults/claude-video/
├── SKILL.md          ← the contract loaded by all surfaces
├── REFERENCE.md      ← quick reference (not loaded by skill runner)
├── README.md         ← upstream public-facing docs
├── scripts/
│   ├── watch.py
│   ├── download.py
│   ├── frames.py
│   ├── transcribe.py
│   ├── whisper.py
│   ├── safe_name.py
│   ├── setup.py
│   └── build-skill.sh
└── dist/
    ├── watch.zip     ← primary cloud artifact for claude.ai upload
    └── watch.skill   ← secondary (renamed ZIP; use only if UI rejects .zip)
```

**Rule:** never edit a file in an installed location (`~/.claude/skills/watch/`, `~/.codex/skills/watch/`, etc.). Always edit in the canonical source, then push the update to each surface.

---

## Update workflow

### 1. Edit in the canonical source

```bash
cd ~/path/to/moreresults/claude-video
# edit SKILL.md, scripts/*, etc.
git add -A && git commit -m "..."
git push
```

### 2. Update Claude Code (manual install)

If installed at `~/.claude/skills/watch` via `git clone`:

```bash
cd ~/.claude/skills/watch
git pull origin main
```

Verify the active file matches the source:

```bash
diff ~/path/to/moreresults/claude-video/SKILL.md ~/.claude/skills/watch/SKILL.md
# should produce no output
```

If the install path differs from the source repo, copy explicitly:

```bash
cp ~/path/to/moreresults/claude-video/SKILL.md ~/.claude/skills/watch/SKILL.md
cp -r ~/path/to/moreresults/claude-video/scripts ~/.claude/skills/watch/
```

**Check `CLAUDE_SKILL_DIR`** — the path Claude Code passes at runtime must point to the installed location, not the source repo (unless they're the same):

```bash
echo $CLAUDE_SKILL_DIR
# should be: /Users/<you>/.claude/skills/watch  (or wherever it's installed)
```

If the variable isn't set in your shell profile or Claude Code config, add it:

```bash
# in ~/.zshrc or ~/.bash_profile:
export CLAUDE_SKILL_DIR="$HOME/.claude/skills/watch"
```

Then reload and verify:

```bash
source ~/.zshrc
echo $CLAUDE_SKILL_DIR
```

### 3. Update claude.ai (web)

claude.ai loads from a ZIP archive unpacked at upload time. It does not auto-refresh from the source.

**ZIP structure required:** the archive must contain the skill folder as its root — not a double-nested subfolder:

```
watch.zip
└── watch/
    ├── SKILL.md
    └── scripts/
        └── ...
```

Build the ZIP:

```bash
cd ~/path/to/moreresults/claude-video
bash scripts/build-skill.sh   # produces dist/watch.zip and dist/watch.skill
```

Verify the ZIP structure before uploading:

```bash
unzip -l dist/watch.zip | head -20
# first entry should be: watch/ or watch/SKILL.md — not just SKILL.md at root
```

Then:
1. Open **Customize → Skills**
2. Find the existing `/watch` skill
3. Delete it (no update-in-place; delete and re-upload is the safe path)
4. Click `+` → `+ Create skill` → upload `dist/watch.zip` (or `dist/watch.skill` if you have confirmed the UI accepts it)

Confirm the upload worked by starting a new conversation and running a short smoke test.

### 4. Update Codex

```bash
cd ~/.codex/skills/watch
git pull origin main
```

### 5. Update Claude Code (plugin install)

Plugin structure for `/watch` packaged as a Claude Code plugin:

```
watch-plugin/
  .claude-plugin/
    plugin.json          ← version field lives here
  skills/
    watch/
      SKILL.md           ← loaded as /watch
      scripts/           ← referenced via ${CLAUDE_PLUGIN_ROOT}/skills/watch/scripts/
```

Scripts inside the plugin must resolve paths using `${CLAUDE_PLUGIN_ROOT}` (bundled plugin files) and `${CLAUDE_PLUGIN_DATA}` (persistent plugin data), not a manually exported `CLAUDE_SKILL_DIR`.

**Version management — critical:**

```json
// .claude-plugin/plugin.json
{
  "name": "watch",
  "version": "0.4.2"   ← must bump this for /plugin update to install new code
}
```

If `version` is omitted entirely, Claude Code uses the git commit SHA as the update key — every commit triggers an update automatically. During active development, omit `version` to avoid having to bump it manually on every change.

If installed via the marketplace:

```bash
/plugin update watch@<marketplace>
/plugin list --json              # confirm installed version
/plugin details watch            # inspect what's loaded
```

If not published to the marketplace (private fork), uninstall the marketplace version and use a local development flow:

```bash
# Remove marketplace version
/plugin remove watch@<marketplace>

# Option A: point Claude Code at the local plugin directory
claude --plugin-dir /path/to/watch-plugin

# Option B: create a local marketplace and install from it
/plugin marketplace add /path/to/local-marketplace
/plugin install watch@<local-marketplace>
```

Validate before installing:

```bash
claude plugin validate ./watch-plugin --strict
```

---

## Verification checklist

After any update, before trusting the skill is current:

### Local skill

```bash
# 1. Source and installed copy match
diff ~/path/to/moreresults/claude-video/SKILL.md ~/.claude/skills/watch/SKILL.md

# 2. Scripts match
diff -r ~/path/to/moreresults/claude-video/scripts ~/.claude/skills/watch/scripts

# 3. CLAUDE_SKILL_DIR points to installed, not source (if separate)
echo $CLAUDE_SKILL_DIR
ls $CLAUDE_SKILL_DIR/SKILL.md

# 4. setup.py runs clean
python3 $CLAUDE_SKILL_DIR/scripts/setup.py --check
# exit 0 = green

# 5. Version
python3 $CLAUDE_SKILL_DIR/scripts/setup.py --version
```

### Claude Code plugin

```bash
claude plugin list --json              # confirm installed version matches what you built
claude plugin details watch            # shows component inventory, contributed skills, token cost
# Confirm version, install path, and skills listed match expectations
```

**Session reload:** run `/reload-plugins` after a plugin update — this switches hooks, MCP servers, and LSP servers to the new path. For the safest verification, start a fresh session, especially when testing skill instructions, monitors, or path-sensitive scripts.

### claude.ai cloud

```bash
# Confirm artifact was built from current source
shasum -a 256 ~/path/to/moreresults/claude-video/dist/watch.zip
# compare against the sha256 you recorded at last upload
```

Start a new conversation after re-uploading. Run a short smoke test (`/watch` on a known short video) to confirm the updated skill loads.

### Codex

```bash
cd ~/.codex/skills/watch
git log --oneline -3   # confirm latest commit matches source
```

---

## Install topology for this project

There are two non-plugin install modes for Claude Code. Use whichever matches your setup:

**User-level (available across all projects):**

```bash
git clone https://github.com/moreresults/claude-video.git ~/.claude/skills/watch
export CLAUDE_SKILL_DIR="$HOME/.claude/skills/watch"
# Set CLAUDE_SKILL_DIR in Claude Code's own env config, not just ~/.zshrc
# On macOS, Claude Code as a GUI app does not source shell profiles
```

**Project-level (checked into a specific repo):**

```bash
git clone https://github.com/moreresults/claude-video.git .claude/skills/watch
# No CLAUDE_SKILL_DIR needed — Claude Code auto-discovers .claude/skills/
```

The project-level path is the cleanest option: the skill travels with the repo, and no env var is needed. Update = `git pull` inside `.claude/skills/watch`.

For the user-level path: source repo = install location eliminates copy-sync. Only the claude.ai ZIP build remains a separate step.

```bash
# Update
cd ~/.claude/skills/watch && git pull

# Verify
diff ~/path/to/moreresults/claude-video/SKILL.md ~/.claude/skills/watch/SKILL.md
```

---

## Build script

`scripts/build-skill.sh` should:

1. Stage all required files (`SKILL.md`, `scripts/`, `REFERENCE.md`, `VERSION`)
2. Create a ZIP with the skill folder as its root: `watch/SKILL.md`, `watch/scripts/...` — never `SKILL.md` at the archive root
3. Output two artifacts:
   - `dist/watch.zip` — primary; confirmed format per Anthropic's help docs
   - `dist/watch.skill` — secondary; a ZIP with a `.skill` extension that some Claude versions accept. Use only if you have confirmed the upload UI accepts it in your environment
4. Print the sha256 of both outputs

```bash
shasum -a 256 dist/watch.zip dist/watch.skill
```

The sha256 gives you a fingerprint to confirm the uploaded version matches what you built. Store it in `VERSION` or a release note so you can verify which build is live in claude.ai.

**Default for uploads: use `watch.zip`.** Fall back to `watch.skill` only if the UI rejects the `.zip` extension.

---

## Infrastructure design: skill-as-package

For a skill with multiple downstream dependents (this one chains to `james-watson-copywriter`, `humanizer`, `markdown-to-apple-deliverable`), treat it like a versioned package.

### Version file

Add `VERSION` to the skill root:

```
0.4.1
```

Reference it in SKILL.md header:

```yaml
version: 0.4.1
```

And at the top of `scripts/watch.py`:

```python
VERSION = "0.4.1"
```

When `setup.py --check` runs, it can emit the version to a log, making it easy to confirm which version Claude loaded in a given session.

### Version consistency check (build gate)

Add `scripts/check_version_consistency.py` and run it as part of every build. It should fail if any of these disagree:

```
VERSION file
SKILL.md frontmatter version field
scripts/watch.py VERSION constant
.claude-plugin/plugin.json version (if explicit-version plugin mode is used)
CHANGELOG.md latest heading
```

```bash
python3 scripts/check_version_consistency.py
# exit 0 = all match; non-zero = print the mismatch and abort build
```

This prevents the silent failure mode where you bump one location and forget another.

### Changelog

`CHANGELOG.md` at the skill root. Entry format:

```
## 0.4.1 — 2026-05-21
- Added --hires-resolution flag
- Step 4.5: added sentinel audit command
- Fixed: safe_name.py now strips em-dashes from folder names
```

### Dependency manifest

`DEPENDENCIES.md` — lists all skills this skill invokes and their minimum versions:

```
james-watson-copywriter >= 1.2.0
humanizer >= 0.3.0
markdown-to-apple-deliverable >= 1.0.0
```

This matters because a broken downstream skill (e.g. humanizer not installed or wrong version) silently produces bad output with no error. The manifest makes the dependency surface explicit.

### Session diagnostics

Add `--version` flag to `setup.py` to print version + install path:

```bash
python3 $CLAUDE_SKILL_DIR/scripts/setup.py --version
# /Users/<you>/.claude/skills/watch (v0.4.1) — ready
```

Use this at the start of any debugging session to confirm what's loaded.

---

## Skill update SOP (short form)

1. Edit in canonical source. Commit and push.
2. `cd ~/.claude/skills/watch && git pull` (if source ≠ install, copy files across)
3. `diff` source vs install to confirm clean
4. If shipping to claude.ai: `bash scripts/build-skill.sh` → re-upload `dist/watch.zip`
5. Run `python3 $CLAUDE_SKILL_DIR/scripts/setup.py --version` in a fresh Claude Code session to confirm the version loaded
6. Run a smoke-test `/watch` on a known short video to confirm end-to-end

---

## What to do when an update doesn't stick

Run this diagnostic in order:

```bash
# Step 1: which SKILL.md is Claude actually loading?
echo $CLAUDE_SKILL_DIR
cat $CLAUDE_SKILL_DIR/SKILL.md | head -5

# Step 2: does it match the source?
diff ~/path/to/moreresults/claude-video/SKILL.md $CLAUDE_SKILL_DIR/SKILL.md

# Step 3: is CLAUDE_SKILL_DIR set in the environment Claude Code inherits?
# On macOS, Claude Code (GUI app) does NOT source ~/.zshrc or ~/.bash_profile
# Set the env var in Claude Code's own settings, not just in the shell profile
# Check: .claude/settings.json or Claude Code preferences for env injection

# Step 4: if using the plugin install — was the version bumped?
claude plugin details watch@<marketplace>   # shows installed version
claude plugin list --json                   # confirm version matches what you built
# Only inspect cache files directly if debugging with claude --debug

# Step 5: for plugin installs — reload
claude plugin update watch@<marketplace>
/reload-plugins
claude plugin details watch@<marketplace>   # confirm new version is loaded
claude plugin list --json

# Step 6: for claude.ai — was the ZIP rebuilt and re-uploaded?
shasum -a 256 ~/path/to/moreresults/claude-video/dist/watch.zip
# compare against the sha256 you recorded at last upload
```

If the plugin updated during an active Claude Code session, run `/reload-plugins`; for the safest verification, start a **fresh session**, especially when testing skill instructions, monitors, or path-sensitive scripts.
