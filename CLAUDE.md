# Constellate: notes for Claude

Constellate is an abstract strategy board game by Matthew Douglas Yglesias (goes by Shmorden). This repo is the
digital edition: one self-contained web page, `index.html`, which GitHub Pages serves to playtesters.
Shmorden directs the work and is not a programmer: explain changes in plain words and keep pull requests easy to review.

## Layout
- `index.html`: the game. Everything (HTML, CSS, JavaScript) is in this one file. It is the ONLY live build; edit it in place.
- `tools/`: Python test tools that drive the game in headless Chromium (Playwright). Run them from the repo root.
- `docs/`: project records (CPU project history, plans).
- `archive/`: two old builds kept for posterity (the oldest build, and the last tiiny.site build). Never edit or test these.
- `res/`: harness output, git-ignored.

Old builds are NOT kept as copies. Git history is the archive; milestones get a git tag (e.g. `build-2026-10-20-x`).

## Branches and pull requests
- `main` is what playtesters get (Pages publishes it). Never commit to `main` directly.
- One task per branch (`feature/team-mode-transfers`, `fix/fleet-popup`, `cleanup/...`), then a pull request into `main`.
- Shmorden tests the branch build on his Android phone before merging. Tell him exactly what to try.
- No broad refactors or file splits without asking first; describe the plan and wait.

## Build stamp and versions (bump on every change that ships)
- The build stamp is in TWO places: `var B="..."` in the error-catcher script in the head, and `const BUILD='...'`. Keep them equal.
- Format: `YYYY-MM-DD-letter`, next letter for each build that day (2026-10-20-x is the base this repo starts from).
- `NET_VER` (online protocol): raise it when an online message changes shape, so mismatched copies refuse to join each other.
- `SHARE_VER` (save codes / share links): raise it only when saved data changes in a way old builds can't read.

## Testing
- Shmorden tests on Android (Chrome, Samsung Internet) constantly and on iPhone when possible. Vibration does nothing on iPhone.
- Smoke test every change in headless Chromium: open the page, play the flow you changed, and check for page errors.
- CPU self-play: `python3 tools/harness.py --n 2 --levels 3,2 --games 150 --out res/x.jsonl`, then `--summary res/x.jsonl`.
  Levels: 1 Easy, 2 Medium, 3 Hard, 4 Hard (legacy), 5 Hard+F (test), 6 Custom.
  Baseline for build 2026-10-20-x: Hard vs Medium 2p = 75.3% win, VP margin +13.75 (150 games). The CPU project recorded 75.0% / +13.6.
- Scoring self-test: `python3 tools/harness.py --check --n 2 --levels 3,2 --games 20` must report 0 mismatches.
- Changes that must not change CPU play (UI work, team mode with teams OFF): record a seeded run on `main` first,
  run the same command on the branch, then `python3 tools/cmp.py res/before.jsonl res/after.jsonl` must say 0 different.
- Other tools: `scen.py` / `scen_defs.py` (hand-built positions), `ab.py` and `pair.py` (compare a Custom variant against Hard),
  `fleetab.py`, `prof.py`, `trace.py`, `scendbg.py`, `runq.sh`. See `docs/CPU_PROJECT.md` for how each was used.
- Long harness runs: keep each command under ~3 minutes, and run in resumable chunks (same `--out` skips finished games).

## Code style
- Comments: one comment block per function (what it does and why), line comments only where something is not obvious.
  Write them so a future session with no memory of this one can follow the code.
- Patch the file with exact-string replacements and check each one matched exactly once; don't rewrite large regions from memory.
- Search `// =====` to see the section map of `index.html`. Main sections, in order: Player look, Move preview, Multi-attack,
  Team mode (data model, transfers), Transcription (fixed positions), iPhone controls, Save codes and share links, History,
  Move log, Shared links, Practice mode, Fixed positions, Themes/Settings, Team mode setup, Players picker, Haptics, Animations,
  Online play, Computer players (turn cache, fast scoring, evaluator, CPU settings page, Hard level, turn planner).

## Standing decisions (don't undo these)
- No "New game" button in the in-game Menu; Concede covers it.
- Free placement is the default; fixed positions are an option.
- The Hold / Retreat choice is called the "Defence call" in the interface (buttons still say Hold and Retreat).
- Online play is live-only and player-hosted (peer to peer).
- Hard CPU strength work is its own project: don't start it unless asked.

## Team mode (in progress)
Team code exists in `index.html` (search `Team mode`) but is half-integrated. Rules and the step plan live in
`docs/` (TEAM_MODE_PLAN_v2.md once added). Goal: finish team mode, then CPUs that play against teams, then CPUs on teams,
without changing any game with teams OFF (prove it with `cmp.py`).
