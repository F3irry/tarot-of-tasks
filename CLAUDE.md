# CLAUDE.md

Guidance for Claude Code when working in this repo.

## Project
Tarot of Tasks: a terminal app that turns a to-do list into a tarot deck.
Read `problem.md` (the original problem) and `spec.md` (the agreed behaviour,
requirement IDs R1–R7) before changing anything.

## Commands
- Run: `py -3.13 tarot.py` (or `py -3.13 tarot.py draw`, `add "..."`, `done`, ...)
- Set up the test environment (once):
  `py -3.13 -m venv .venv` then `.venv\Scripts\python -m pip install -r requirements-dev.txt`
- Test: `.venv\Scripts\python -m pytest`

## Rules
- Always use Python 3.13 through the `py -3.13` launcher. The `python` on PATH
  is 3.8, so never use it.
- The app itself uses only the standard library. pytest is the only dev dependency.
- Every test name includes the requirement ID it checks, for example
  `test_R4_done_removes_card_for_good`. New behaviour needs a spec entry and an ID first.
- Ask the user before resolving anything ambiguous in `problem.md` or `spec.md`.
- Keep commits small, with messages that say what changed and why.
  Never undo, amend, or force-push a commit.
- `deck.json` holds the user's personal tasks. It is gitignored, so never commit it.
- Tests must never touch the real `deck.json`. Point `TAROT_DECK` at a temp path.

## Layout
- `tarot.py`: everything. The deck model (`Deck`), card art (`face_rows`,
  `back_rows`, `build_card`, `compose`), animations, commands, and the CLI.
- `test_tarot.py`: pytest tests (logic, rendering geometry, end-to-end CLI).
