#!/usr/bin/env python3
"""Tarot of Tasks: gamble on your next task.

Your to-do list becomes a deck of tarot cards. Shuffle, draw, face your fate,
and burn the card when the task is done.

    py -3.13 tarot.py                 interactive menu
    py -3.13 tarot.py add "task" ...  inscribe tasks into the deck
    py -3.13 tarot.py draw            shuffle and draw your fate
    py -3.13 tarot.py done [N]        burn the card in your hand (or card N)
    py -3.13 tarot.py return          put the drawn card back (the deck will judge you)
    py -3.13 tarot.py list            see the whole deck
    py -3.13 tarot.py shuffle         shuffle the deck

Pure standard library (Python 3.13 via the py launcher). Set TAROT_DECK to use a different deck
file, TAROT_NO_ANIM=1 or --no-anim to skip animations, NO_COLOR=1 for plain text.
"""

import argparse
import json
import math
import os
import random
import shutil
import sys
import textwrap
import time
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DECK = os.path.join(APP_DIR, "deck.json")
RUN = "py -3.13 tarot.py"  # how the user runs the app, shown in hints


def deck_path():
    return os.environ.get("TAROT_DECK") or DEFAULT_DECK


# --------------------------------------------------------------------------
# Flavour text
# --------------------------------------------------------------------------

ARCANA = [
    "The Procrastinator", "The Overdue", "The Tower of Dishes", "The Unread Inbox",
    "Wheel of Errands", "The Hermit of Chores", "The Lingering", "Queen of Deadlines",
    "Knight of Laundry", "The Looming", "The Unopened Letter", "Ace of Admin",
    "The Dread", "Judgement Day", "The Reckoning", "Page of Paperwork",
    "The Hanged To-Do", "Death of Excuses", "The Fool Who Waited", "Strength, Unused",
    "The Star of Someday", "The Moon of Maybe", "The Sun of Done", "Temperance of Tabs",
    "King of Backlog", "The Chariot of Chores", "The Lovers of Later",
    "The Devil You Defer", "Seven of Sighs", "The Empress of Errands",
    "Ten of To-Dos", "The High Priestess of Pending", "The Magician of Maybe",
]

FORTUNES = [
    "The cards have spoken. They did not stutter.",
    "Fate has chosen. Your opinion was not requested.",
    "This card has waited long enough. So have you.",
    "The spirits are watching. So far, they are unimpressed.",
    "No more shuffling. You drew it. You do it.",
    "Destiny is not a suggestion.",
    "The stars aligned for this. Do not make them realign.",
    "Every minute you stare at this card, it grows heavier.",
    "Begin badly if you must. But begin.",
    "Even the Fool starts walking. Start walking.",
    "Your future self is watching through the veil. They are begging.",
    "The candle is lit. It will not burn forever. Neither will your excuses.",
    "This is the omen you asked for. Go.",
    "Five minutes. The cards demand only five minutes. Then we'll talk.",
    "The moon has watched you avoid this for weeks. The moon remembers.",
    "You cannot out-wait a tarot deck. We are made of patience and paper.",
    "The prophecy is clear: you will do this, and then you will feel smug.",
    "Somewhere a crow is cawing your name. It is saying 'get on with it.'",
    "The card glows because it is ready. Are you?",
    "Lesser mortals would flinch. You will not flinch.",
    "The ancients carved this task into stone. It is still not done.",
    "Do it now and the next card will be kinder. (No promises.)",
    "Doubt is not a card in this deck.",
    "The dice have been rolled. You rolled them, technically. Own it.",
    "Hesitation angers the deck. Do not anger the deck.",
    "Your reading is complete. Stop reading. Start doing.",
    "There is no reversed meaning. There is only doing it.",
    "The Oracle checked. There is no tomorrow where this is easier.",
    "The veil parts. Behind it: this task. Sorry.",
    "It is written. In ink. On a card. In your own handwriting.",
    "Small steps still count as steps. Big sulks do not.",
    "This card chose you because it knew you could. Prove it right.",
    "Light a candle, set a timer, and face your fate.",
    "The fates are on a tight schedule. Get moving.",
    "Your excuses have been shuffled out of the deck.",
    "The crystal ball shows you finished, smug, and free. Go make it true.",
    "Arise. The card has called you to battle.",
    "This task fears you more than you fear it.",
    "The deck is old and has outlived many procrastinators. Do not join them.",
    "A thousand tarot readers agree: this one. Now.",
]

RETURN_SCOLDS = [
    "The deck takes it back. The deck is disappointed.",
    "Returned. The card will remember this betrayal.",
    "Back into the shuffle it goes. It will find you again.",
    "Cowardice noted in the ledger of fate.",
    "Fine. But the cards always come back around.",
]

EPITAPHS = [
    "Burned to ash. The deck grows lighter.",
    "One fewer ghost haunting the deck.",
    "The fates nod, almost impressed.",
    "Victory. The cards will whisper of this.",
    "Done. Breathe. Then draw again, brave one.",
    "The prophecy is fulfilled. Smugness is permitted.",
    "Ash and glory. Mostly ash.",
]

EMPTY_DECK = ("The deck is empty. Either you have conquered everything, or you "
              "have not written anything down. The cards suspect the latter.")


# --------------------------------------------------------------------------
# The deck (data + persistence)
# --------------------------------------------------------------------------

class TarotError(Exception):
    """A user-facing problem, printed nicely instead of as a traceback."""


class Deck:
    def __init__(self, path):
        self.path = path
        self.next_id = 1
        self.cards = []        # index 0 is the top of the deck
        self.drawn = None      # the card in your hand, if any
        self.graveyard = []    # finished tasks
        self.load()

    # persistence ----------------------------------------------------------
    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (ValueError, OSError) as e:
            raise TarotError(
                "The deck at {} is damaged ({}). Fix it or move it aside; "
                "I won't overwrite it.".format(self.path, e))
        self.next_id = data.get("next_id", 1)
        self.cards = data.get("cards", [])
        self.drawn = data.get("drawn")
        self.graveyard = data.get("graveyard", [])

    def save(self):
        folder = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(folder, exist_ok=True)
        tmp = self.path + ".tmp"
        data = {
            "next_id": self.next_id,
            "cards": self.cards,
            "drawn": self.drawn,
            "graveyard": self.graveyard,
        }
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    # operations -----------------------------------------------------------
    def all_cards(self):
        return ([self.drawn] if self.drawn else []) + self.cards

    def add(self, task):
        task = " ".join(task.split())
        if not task:
            raise TarotError("A blank card holds no fate. Write an actual task.")
        used = {c["arcana"] for c in self.all_cards()}
        free = [a for a in ARCANA if a not in used] or ARCANA
        card = {
            "id": self.next_id,
            "task": task,
            "arcana": random.choice(free),
            "added": datetime.now().isoformat(timespec="seconds"),
        }
        self.next_id += 1
        self.cards.insert(random.randint(0, len(self.cards)), card)
        return card

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self):
        if self.drawn:
            raise TarotError("You already hold a card. Finish it or return it.")
        if not self.cards:
            raise TarotError(EMPTY_DECK)
        self.drawn = self.cards.pop(0)
        return self.drawn

    def return_card(self):
        if not self.drawn:
            raise TarotError("Your hand is empty. There is nothing to return.")
        card = self.drawn
        self.drawn = None
        self.cards.insert(random.randint(0, len(self.cards)), card)
        return card

    def discard(self, card_id=None):
        if card_id is None:
            if not self.drawn:
                raise TarotError("Your hand is empty. Draw a card first, or name "
                                 "one: {} done <number>.".format(RUN))
            card, self.drawn = self.drawn, None
        elif self.drawn and self.drawn["id"] == card_id:
            card, self.drawn = self.drawn, None
        else:
            for i, c in enumerate(self.cards):
                if c["id"] == card_id:
                    card = self.cards.pop(i)
                    break
            else:
                raise TarotError("No card numbered {} lives in this deck."
                                 .format(card_id))
        done = dict(card)
        done["done"] = datetime.now().isoformat(timespec="seconds")
        self.graveyard.append(done)
        return card


def roman(n):
    if n <= 0:
        return "0"
    out = ""
    for value, numeral in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
                           (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
                           (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out += numeral
            n -= value
    return out


# --------------------------------------------------------------------------
# Terminal output
# --------------------------------------------------------------------------

COLOR = False
ANIMATE = False

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
ITALIC = "\x1b[3m"

GOLD = (232, 185, 35)
PALE_GOLD = (255, 236, 160)
GLOW_WHITE = (255, 250, 225)
PURPLE = (150, 100, 220)
INDIGO = (85, 65, 160)
WHITE = (245, 240, 255)
CRIMSON = (230, 70, 90)
FLAME = (255, 210, 90)
EMBER = (255, 110, 40)
ASH = (95, 90, 100)
DUSK = (35, 22, 48)
MUTED = (150, 140, 170)

W = 28          # inner width of a card
H = 15          # inner height of a card
MARGIN = "    "


def setup_terminal(no_anim=False):
    global COLOR, ANIMATE
    if os.name == "nt":
        os.system("")  # switches the Windows console into ANSI mode
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tty = sys.stdout.isatty()
    COLOR = tty and not os.environ.get("NO_COLOR")
    tall_enough = shutil.get_terminal_size((80, 24)).lines >= 24
    ANIMATE = (tty and tall_enough and not no_anim
               and not os.environ.get("TAROT_NO_ANIM"))


def fg(rgb):
    return "\x1b[38;2;{};{};{}m".format(*rgb) if COLOR else ""


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def pause(seconds):
    if ANIMATE:
        sys.stdout.flush()
        time.sleep(seconds)


def cells(text, rgb=None, bold=False):
    return [(ch, rgb, bold) for ch in text]


def to_ansi(line):
    """Turn a list of (char, rgb, bold) cells into a printable string."""
    if not COLOR:
        return "".join(ch for ch, _, _ in line)
    out, current = [], None
    for ch, rgb, bold in line:
        style = None if (ch == " " or rgb is None) else (rgb, bold)
        if style != current:
            out.append(RESET)
            if style:
                out.append((BOLD if bold else "") + fg(rgb))
            current = style
        out.append(ch)
    out.append(RESET)
    return "".join(out)


def visible_len(s):
    """Length of a string with ANSI codes stripped (for tests)."""
    out, i = 0, 0
    while i < len(s):
        if s[i] == "\x1b":
            while i < len(s) and not s[i].isalpha():
                i += 1
        else:
            out += 1
        i += 1
    return out


def say(text, rgb=WHITE, italic=False, bold=False, typing=False, center=True,
        width=None):
    if width is None:
        # Centred text sits under the card; left-aligned text can use the line.
        width = W + 2 if center else 76
    style = ""
    if COLOR:
        style = (ITALIC if italic else "") + (BOLD if bold else "") + fg(rgb)
    for line in textwrap.wrap(text, width) or [""]:
        if center:
            pad = " " * max(0, (W + 6 - len(line)) // 2)
        else:
            pad = ""
        sys.stdout.write(MARGIN + pad + style)
        if typing and ANIMATE:
            for ch in line:
                sys.stdout.write(ch)
                pause(0.018)
        else:
            sys.stdout.write(line)
        sys.stdout.write((RESET if COLOR else "") + "\n")
    sys.stdout.flush()


class Stage:
    """Redraws a block of lines in place, for animation."""

    def __init__(self):
        self.height = 0

    def show(self, lines):
        buf = ["\x1b[?25l"] if ANIMATE else []  # hide cursor while animating
        if self.height and ANIMATE:
            buf.append("\x1b[{}A\r".format(self.height))
        clear = "\x1b[2K" if ANIMATE else ""
        for line in lines:
            buf.append(clear + line + "\n")
        sys.stdout.write("".join(buf))
        sys.stdout.flush()
        self.height = len(lines)

    def clear(self):
        if self.height and ANIMATE:
            up = "\x1b[{}A\r".format(self.height)
            sys.stdout.write(up + "\x1b[2K\n" * self.height + up)
            sys.stdout.flush()
        self.height = 0


# --------------------------------------------------------------------------
# Card art
# --------------------------------------------------------------------------

def face_rows(card):
    """Inner rows of a card's face: list of (text, rgb, bold), each W wide."""
    num = roman(card["id"])
    rows = []

    def row(text, rgb=WHITE, bold=False):
        rows.append((text.ljust(W)[:W], rgb, bold))

    row(" " + num.ljust(W - 5) + " ✦ ", GOLD, True)
    row("")
    row("✧ · ✦ · ✧".center(W), PURPLE)
    row("")
    lines = textwrap.wrap(card["task"], W - 6) or [""]
    if len(lines) > 6:
        lines = lines[:6]
        lines[-1] = lines[-1][:W - 7] + "…"
    top = (6 - len(lines)) // 2
    lines = [""] * top + lines + [""] * (6 - top - len(lines))
    for text in lines:
        row(text.center(W), WHITE, True)
    row("")
    row("── ◆ ──".center(W), GOLD)
    row(card["arcana"][:W - 2].center(W), PALE_GOLD, True)
    row("")
    row(" ✦ " + (num + " ").rjust(W - 3), GOLD, True)
    return rows


def back_rows():
    base = "· ✦ · ✧ " * 10
    rows = []
    for r in range(H):
        offset = (r * 2) % 8
        rows.append((base[offset:offset + W], INDIGO if r % 2 else PURPLE, False))
    medallion = [
        "╭" + "─" * 11 + "╮",
        "│" + "✦ ◆ ✦".center(11) + "│",
        "│" + "TAROT".center(11) + "│",
        "│" + "OF  TASKS".center(11) + "│",
        "╰" + "─" * 11 + "╯",
    ]
    start = (W - 13) // 2
    for i, m in enumerate(medallion):
        r = 5 + i
        text = rows[r][0]
        rows[r] = (text[:start] + m + text[start + len(m):], GOLD, True)
    return rows


def build_card(rows, inner_w=W, border=GOLD):
    """Card as cell-lines, each W+2 wide; inner_w < W squeezes it (for flips)."""
    pad_l = (W - inner_w) // 2
    pad_r = W - inner_w - pad_l
    left, right = cells(" " * pad_l), cells(" " * pad_r)
    lines = [left + cells("╔" + "═" * inner_w + "╗", border) + right]
    for text, rgb, bold in rows:
        lines.append(left + cells("║", border)
                     + cells(text[pad_l:pad_l + inner_w], rgb, bold)
                     + cells("║", border) + right)
    lines.append(left + cells("╚" + "═" * inner_w + "╝", border) + right)
    return lines


def compose(card_lines, glow=0.0):
    """Wrap a card in a two-ring halo whose brightness is `glow` (0..1)."""
    width = len(card_lines[0])
    if glow > 0.05:
        o = cells("░", lerp(DUSK, GOLD, glow * 0.75))
        i = cells("▒", lerp(DUSK, PALE_GOLD, glow))
    else:
        o = i = cells(" ")
    out = [o * (width + 4), o + i * (width + 2) + o]
    out += [o + i + line + i + o for line in card_lines]
    out += [o + i * (width + 2) + o, o * (width + 4)]
    return [MARGIN + to_ansi(line) for line in out]


def card_frame(card, glow=0.6):
    border = lerp(GOLD, GLOW_WHITE, glow)
    return compose(build_card(face_rows(card), W, border), glow)


MINI = ["╭─────╮", "│✦·✧·✦│", "│·✧◆✧·│", "│✦·✧·✦│", "╰─────╯"]


def shuffle_anim(n_cards):
    if not ANIMATE:
        return
    stage = Stage()
    width, height = W + 10, 7
    count = max(1, min(3, n_cards))
    for k in range(20):
        grid = [cells(" " * width) for _ in range(height)]
        for i in range(count):
            x = (width - 7) // 2 + int(round(10 * math.sin(k * 0.8 + i * 2.1)))
            y = (k + i) % 2
            for r, line in enumerate(MINI):
                for c, ch in enumerate(line):
                    if ch in "╭╮╰╯─│":
                        rgb = GOLD
                    elif ch == "◆":
                        rgb = PALE_GOLD
                    else:
                        rgb = PURPLE
                    grid[y + r][x + c] = (ch, rgb, False)
        caption = ("shuffling the fates" + "." * (k % 4)).ljust(22).center(width)
        grid[6] = cells(caption, MUTED)
        stage.show([MARGIN + to_ansi(row) for row in grid])
        pause(0.07)
    stage.clear()


def flip_anim(card):
    stage = Stage()
    if not ANIMATE:
        stage.show(card_frame(card))
        return
    back, face = back_rows(), face_rows(card)
    stage.show(compose(build_card(back)))
    pause(0.6)
    for w in range(W, -1, -4):
        stage.show(compose(build_card(back, w)))
        pause(0.04)
    for w in range(0, W + 1, 4):
        stage.show(compose(build_card(face, w)))
        pause(0.04)
    frames = 40
    for k in range(frames + 1):
        t = k / frames
        glow = min(1.0, t * 3) * (0.6 + 0.4 * math.sin(t * math.pi * 5))
        stage.show(card_frame(card, glow))
        pause(0.04)


def burn_anim(card):
    if not ANIMATE:
        return
    base = build_card(face_rows(card))
    rnd = random.Random()
    thresholds = [[rnd.random() * 0.85 for _ in line] for line in base]
    stage = Stage()
    frames = 26
    for k in range(frames + 1):
        p = 1.2 * k / frames
        lines = []
        for li, line in enumerate(base):
            out = []
            for ci, (ch, rgb, bold) in enumerate(line):
                if rgb is None:
                    out.append((ch, None, False))
                    continue
                age = p - thresholds[li][ci]
                if age < 0:
                    heat = max(0.0, 1 + age / 0.25)
                    out.append((ch, lerp(rgb, EMBER, heat * 0.8), bold))
                elif age < 0.06:
                    out.append(("▓", FLAME, True))
                elif age < 0.12:
                    out.append(("▒", EMBER, False))
                elif age < 0.2:
                    out.append(("░", lerp(EMBER, ASH, 0.5), False))
                elif age < 0.3:
                    out.append(("·", ASH, False))
                else:
                    out.append((" ", None, False))
            lines.append(out)
        stage.show(compose(lines))
        pause(0.06)
    stage.clear()


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def banner():
    print()
    say("✦ ─── T A R O T   O F   T A S K S ─── ✦", GOLD, bold=True)
    print()


def hint(text):
    say(text, MUTED, center=False)


def cmd_add(deck, tasks):
    if not tasks:
        say("Inscribe your tasks. An empty line seals the deck.", MUTED,
            center=False)
        tasks = []
        while True:
            try:
                line = input(MARGIN + "✦ ")
            except EOFError:
                break
            if not line.strip():
                break
            tasks.append(line)
    added = 0
    for task in tasks:
        if not task.strip():
            continue
        card = deck.add(task)
        added += 1
        say("{} · {} · sealed into the deck".format(
            roman(card["id"]), card["arcana"]), GOLD, center=False)
    if added:
        deck.save()
        hint("The deck now holds {} card{}.".format(
            len(deck.cards), "" if len(deck.cards) == 1 else "s"))


def cmd_draw(deck):
    if deck.drawn:
        print()
        say("You already hold a card.", CRIMSON, bold=True)
        for line in card_frame(deck.drawn):
            print(line)
        hint("Finish it:           {} done".format(RUN))
        hint("Return it in shame:  {} return".format(RUN))
        return
    if not deck.cards:
        print()
        say(EMPTY_DECK, CRIMSON, italic=True)
        hint('Add tasks with:  {} add "do the thing"'.format(RUN))
        return
    print()
    shuffle_anim(len(deck.cards))
    deck.shuffle()
    card = deck.draw()
    deck.save()  # save before the show, so Ctrl+C mid-animation loses nothing
    flip_anim(card)
    print()
    say("“" + random.choice(FORTUNES) + "”", CRIMSON, italic=True, typing=True)
    print()
    hint("When it's done:  {} done".format(RUN))
    hint("Cowardice:       {} return".format(RUN))


def cmd_done(deck, card_id=None):
    card = deck.discard(card_id)
    deck.save()
    print()
    if ANIMATE:
        burn_anim(card)
    say("✦ {} burns: {}".format(card["arcana"], card["task"]), EMBER, bold=True)
    say(random.choice(EPITAPHS), PALE_GOLD, italic=True, typing=True)
    left = len(deck.cards)
    hint("{} card{} remain{}.  ·  {} conquered so far.".format(
        left, "" if left == 1 else "s", "s" if left == 1 else "",
        len(deck.graveyard)))
    print()


def cmd_return(deck):
    card = deck.return_card()
    deck.save()
    print()
    say("{} slinks back into the deck.".format(card["arcana"]), PURPLE)
    say(random.choice(RETURN_SCOLDS), CRIMSON, italic=True, typing=True)
    print()


def cmd_list(deck):
    print()
    total = len(deck.all_cards())
    say("THE DECK · {} card{}".format(total, "" if total == 1 else "s"),
        GOLD, bold=True, center=False)
    if deck.drawn:
        c = deck.drawn
        say("in hand  {:>8}  {}  ·  {}".format(roman(c["id"]), c["arcana"],
                                               c["task"]),
            PALE_GOLD, bold=True, center=False, width=100)
    for c in sorted(deck.cards, key=lambda c: c["id"]):
        say("         {:>8}  {}  ·  {}".format(roman(c["id"]), c["arcana"],
                                               c["task"]),
            WHITE, center=False, width=100)
    if not total:
        say(EMPTY_DECK, CRIMSON, italic=True, center=False, width=70)
    if deck.graveyard:
        say("Ashes: {} task{} conquered.".format(
            len(deck.graveyard), "" if len(deck.graveyard) == 1 else "s"),
            MUTED, center=False)
    hint("Finish any card by number:  {} done 3".format(RUN))
    print()


def cmd_shuffle(deck):
    print()
    shuffle_anim(len(deck.cards))
    deck.shuffle()
    deck.save()
    say("The deck is shuffled. Fate is reset.", PURPLE, italic=True)
    print()


def parse_card_number(text):
    text = text.strip()
    if text.isdigit():
        return int(text)
    upper = text.upper()
    for n in range(1, 4000):
        if roman(n) == upper:
            return n
    raise TarotError("'{}' is not a card number.".format(text))


def menu(deck):
    banner()
    while True:
        total = len(deck.all_cards())
        status = "{} card{} in the deck".format(total, "" if total == 1 else "s")
        if deck.drawn:
            status += "  ·  in hand: " + deck.drawn["arcana"]
        say(status, MUTED, center=False)
        say("[d]raw  [a]dd  [f]inish  [r]eturn  [l]ist  [s]huffle  [q]uit",
            GOLD, center=False, width=80)
        try:
            if ANIMATE:
                sys.stdout.write("\x1b[?25h")  # show cursor for typing
            choice = input(MARGIN + "› ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        try:
            if choice in ("q", "quit", "exit"):
                say("The cards will wait. They are very good at waiting.",
                    PURPLE, italic=True)
                print()
                return
            elif choice in ("d", "draw"):
                cmd_draw(deck)
            elif choice in ("a", "add"):
                cmd_add(deck, [])
            elif choice in ("f", "finish", "done"):
                if deck.drawn:
                    cmd_done(deck)
                else:
                    raw = input(MARGIN + "Card number to burn (blank to cancel): ")
                    if raw.strip():
                        cmd_done(deck, parse_card_number(raw))
            elif choice in ("r", "return"):
                cmd_return(deck)
            elif choice in ("l", "list"):
                cmd_list(deck)
            elif choice in ("s", "shuffle"):
                cmd_shuffle(deck)
            elif choice:
                say("The cards do not understand '{}'.".format(choice), CRIMSON,
                    center=False)
        except TarotError as e:
            say(str(e), CRIMSON, italic=True, center=False, width=70)
            print()
        except (EOFError, KeyboardInterrupt):
            print()
            return


def build_parser():
    p = argparse.ArgumentParser(
        prog="tarot", description="Tarot of Tasks: gamble on your next task.")
    p.add_argument("--no-anim", action="store_true", help="skip animations")
    sub = p.add_subparsers(dest="command")
    a = sub.add_parser("add", help="inscribe tasks into the deck")
    a.add_argument("tasks", nargs="*", help="one or more tasks (quote each)")
    sub.add_parser("draw", help="shuffle and draw your fate")
    d = sub.add_parser("done", aliases=["discard", "finish", "burn"],
                       help="burn the card in your hand, or card N")
    d.add_argument("number", nargs="?", help="card number (e.g. 3 or III)")
    sub.add_parser("return", help="put the drawn card back in the deck")
    sub.add_parser("list", help="show every card in the deck")
    sub.add_parser("shuffle", help="shuffle the deck")
    sub.add_parser("menu", help="interactive menu (the default)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    setup_terminal(no_anim=args.no_anim)
    try:
        deck = Deck(deck_path())
        cmd = args.command
        if cmd in (None, "menu"):
            menu(deck)
        elif cmd == "add":
            cmd_add(deck, args.tasks)
        elif cmd == "draw":
            cmd_draw(deck)
        elif cmd in ("done", "discard", "finish", "burn"):
            number = parse_card_number(args.number) if args.number else None
            cmd_done(deck, number)
        elif cmd == "return":
            cmd_return(deck)
        elif cmd == "list":
            cmd_list(deck)
        elif cmd == "shuffle":
            cmd_shuffle(deck)
        return 0
    except TarotError as e:
        print()
        say(str(e), CRIMSON, italic=True, center=False, width=70)
        print()
        return 1
    except KeyboardInterrupt:
        print()
        return 130
    finally:
        if ANIMATE:
            sys.stdout.write(RESET + "\x1b[?25h")
            sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main())
