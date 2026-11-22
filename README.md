# Tarot of Tasks

Don't know where to start on your to-do list? Let fate decide.

Tarot of Tasks turns your tasks into a deck of tarot cards in the terminal.
Shuffle the deck and draw a card. It flips over, glows gold, and reveals your
next task, along with a whimsical, slightly menacing message telling you to get on
with it. When you're done, burn the card and it's gone from the deck for good.

```
    ░▒╔════════════════════════════╗▒░
    ░▒║ XIV                     ✦  ║▒░
    ░▒║         ✧ · ✦ · ✧          ║▒░
    ░▒║    Write the quarterly     ║▒░
    ░▒║    report for the team     ║▒░
    ░▒║          ── ◆ ──           ║▒░
    ░▒║   The Empress of Errands   ║▒░
    ░▒║ ✦                      XIV ║▒░
    ░▒╚════════════════════════════╝▒░

      “The Oracle checked. There is
        no tomorrow where this is
                 easier.”
```
(The real card is taller, in full 24-bit colour, with shuffle, flip, glow and burn animations.)

## Run

Needs Python 3.13 through the Windows `py` launcher. There are no dependencies to install.

```
py -3.13 tarot.py
```

First it asks for tasks you need to complete, one per line. Press Enter on an
empty line to finish, or right away if your deck is already full. Then it
shuffles and draws a card. Once the card is revealed, press a single key:

| Key | What it does |
| --- | --- |
| **d** | Done: burn the card, then draw the next one |
| **r** | Return the card to the deck, then draw again |
| **q** | Quit. The card stays in your hand for next time |

You can also run a single command:

| Command | What it does |
| --- | --- |
| `py -3.13 tarot.py add "task" "another task"` | Seal tasks into the deck |
| `py -3.13 tarot.py draw` | Shuffle, draw, flip, glow, and get your orders |
| `py -3.13 tarot.py done` (or `d`) | Burn the card in your hand (finished!) |
| `py -3.13 tarot.py done 3` (or `d 3`) | Burn card number 3 (or `III`) straight from the deck |
| `py -3.13 tarot.py return` (or `r`) | Put the drawn card back. The deck will judge you |
| `py -3.13 tarot.py list` | See every card, the one in your hand, and your tally of burned cards |
| `py -3.13 tarot.py shuffle` | Shuffle the deck |
| `py -3.13 tarot.py menu` | The interactive menu: **d**raw, **a**dd, **f**inish, **r**eturn, **l**ist, **s**huffle, **q**uit |

You hold one card at a time. Finish it or return it before drawing again.

Your deck is saved to `deck.json` next to `tarot.py`. Git ignores it, so your
tasks stay private. Options: `--no-anim` (or `TAROT_NO_ANIM=1`) skips the
animations, `NO_COLOR=1` turns off colour, and `TAROT_DECK=path` uses a different deck file.

## Test

One-time setup, which creates a virtual environment with pytest:

```
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

Run the tests:

```
.venv\Scripts\python -m pytest
```

Each test name includes the requirement it checks (R1–R9). They are defined in
[spec.md](spec.md), which builds on the original [problem.md](problem.md).
