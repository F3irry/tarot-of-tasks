# Tarot of Tasks: Specification

Source: `problem.md`. This spec turns its initial requirements (R1–R5) into
testable behaviour and records the decisions made where the problem statement
left room for interpretation.

## Overview

A command-line app, written in Python 3.13 using only the standard library, that turns a to-do list
into a deck of tarot cards. You shuffle, draw a card, and that is your next
task. Starting feels like a gamble instead of a chore.

- **Run:** `py -3.13 tarot.py` (enter tasks, then draw: see R8) or
  `py -3.13 tarot.py <command>`
- **Commands:** `add`, `draw`, `done` (aliases `d`, `discard`, `finish`, `burn`),
  `return` (alias `r`), `list`, `shuffle`, `menu` (the interactive menu)
- **Storage:** `deck.json` next to `tarot.py`. Git ignores it because it holds
  personal tasks. Set the `TAROT_DECK` environment variable to override the path.

## Requirements

### R1: Tasks become cards in a deck saved between runs
- `add "task" ["task" ...]` creates one card per task. With no arguments,
  `add` prompts for tasks one per line, and an empty line finishes.
- Each card gets a unique, never-reused number (`id`, shown as a Roman numeral),
  a tarot-style name (its "arcana"), and a creation timestamp.
- Whitespace is collapsed. A blank task is rejected with a friendly error.
- The deck, the card in hand, and the finished cards are written to JSON after every
  change, and a write never leaves a half-written file behind.
- If the JSON file is unreadable, the app reports it and **does not overwrite it**.

### R2: Shuffle and draw; the card flips and is revealed with a glow
- `shuffle` randomises the deck order and plays a shuffle animation.
- `draw` shuffles, then takes the top card into your **hand**. The card leaves the
  deck until it is finished (R4) or returned (R6).
- Only one card can be in hand. Drawing again shows the held card and tells you
  to finish or return it.
- Drawing from an empty deck shows a message instead of crashing.
- Animation: a shuffle of small card backs, then the card back flips over
  (it squeezes to nothing and opens up as the face), then a pulsing golden halo
  that settles into a steady glow.
- The deck is saved **before** the animation, so pressing Ctrl+C partway through loses nothing.

### R3: Every draw comes with a whimsical, daunting, hardass message
- On each draw, a message is picked at random from a built-in pool of at least 30.
  It is not tied to the card.
- Putting a card back (R6) and finishing one (R4) also get their own flavour lines.

### R4: Throwing away a finished card removes it for good
- `done` throws away the card in hand. `done N` throws away card number N
  (written as a number or a Roman numeral), whether it is in hand or still in the deck.
- A thrown-away card never comes back in a future draw. It moves to a
  `graveyard` list, which is used only for the "conquered" count.
- Plays a burning animation, then an epitaph line.
- `done` with an empty hand, or with an unknown number, is a friendly error.

### R5: The cards look striking in the terminal
- A card is a 30×17 box-drawn frame (28×15 inside), with Roman numerals in the corners,
  ornaments, the wrapped task text (at most 6 lines, truncated with `…`), and
  the arcana name. The card back has a lattice pattern and a "TAROT OF TASKS"
  medallion.
- Uses 24-bit colour: gold, purple, white, crimson, and ember colours.
- Every animation frame is a rectangle of fixed size, so frames redraw cleanly
  in place.
- When output is not a terminal, or `NO_COLOR` is set, the app prints no escape codes.
  Animations are skipped when output is not a terminal, when the terminal is
  shorter than 24 rows, or when `--no-anim` or `TAROT_NO_ANIM` is set.

### R6: Return a drawn card (derived from R2)
- `return` puts the card in hand back at a random position in the deck, with a scolding.

### R7: Friendly failure (derived)
- Every expected problem (empty deck, empty hand, bad number, blank task,
  damaged file) prints a styled message and exits with code 1, with no traceback.

### R8: Enter tasks before shuffling (round 2)
- Running the app with no arguments first asks for tasks, one per line. An empty
  line (or end of input) finishes. The tasks are added as in R1, and entering
  none is fine.
- Then it shuffles and draws as in R2 and asks for a quick key (R9).
- If a card is already in hand, it is shown and you get the quick keys for it.
  Nothing new is drawn until it is finished or returned (R2's one-card rule).
- After `d` or `r`, the next card is shuffled and drawn, and you get the keys again.
  This repeats until you quit or the deck is empty. An empty deck shows a message
  and exits with code 0.
- The interactive menu that used to be the default is now `menu`.

### R9: Quick keys after a draw (round 2)
- After a card is revealed by the no-argument flow, a single key press decides:
  `d` = done (burn it, as in R4), `r` = return it (R6), `q` = quit and keep
  the card in hand. Keys are case-insensitive and need no Enter when input is a
  terminal. When input is piped, the first character of each line is used.
- Any other key gets a short reminder and asks again. End of input or Ctrl+C
  counts as `q`.
- Command aliases: `d` for `done` (so `d 3` works too) and `r` for `return`.

## Out of scope (round 1)
Due dates, priorities, multiple decks, editing a card's text, undo.
