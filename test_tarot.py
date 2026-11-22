"""Tests for Tarot of Tasks. Each test name carries the spec.md requirement ID.

Run:  .venv\\Scripts\\python -m pytest
"""

import json
import os
import subprocess
import sys

import pytest

import tarot

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def deck_file(tmp_path):
    return str(tmp_path / "deck.json")


@pytest.fixture
def deck(deck_file):
    return tarot.Deck(deck_file)


@pytest.fixture
def plain_render(monkeypatch):
    monkeypatch.setattr(tarot, "COLOR", True)
    monkeypatch.setattr(tarot, "ANIMATE", False)


# --- R1: tasks become cards, saved between runs ---------------------------

def test_R1_add_creates_card_with_id_arcana_and_tidy_text(deck):
    a = deck.add("  wash   the dishes ")
    b = deck.add("call mum")
    assert (a["id"], b["id"]) == (1, 2)
    assert a["task"] == "wash the dishes"
    assert a["arcana"] in tarot.ARCANA
    assert a["arcana"] != b["arcana"]
    assert "added" in a


def test_R1_blank_task_is_rejected(deck):
    with pytest.raises(tarot.TarotError):
        deck.add("   ")


def test_R1_deck_persists_between_runs(deck, deck_file):
    deck.add("one")
    deck.add("two")
    deck.draw()
    deck.save()
    again = tarot.Deck(deck_file)
    assert len(again.all_cards()) == 2
    assert again.drawn is not None
    assert again.next_id == 3


def test_R1_save_leaves_no_temp_file(deck, deck_file):
    deck.add("one")
    deck.save()
    assert os.path.exists(deck_file)
    assert not os.path.exists(deck_file + ".tmp")


def test_R1_damaged_deck_file_is_not_overwritten(deck_file):
    with open(deck_file, "w") as f:
        f.write("{not json")
    with pytest.raises(tarot.TarotError):
        tarot.Deck(deck_file)
    with open(deck_file) as f:
        assert f.read() == "{not json"


# --- R2: shuffle and draw --------------------------------------------------

def test_R2_draw_moves_top_card_into_hand(deck):
    for t in "abc":
        deck.add(t)
    top = deck.cards[0]
    assert deck.draw() is top
    assert deck.drawn is top
    assert top not in deck.cards
    assert len(deck.cards) == 2


def test_R2_only_one_card_in_hand(deck):
    deck.add("a")
    deck.add("b")
    deck.draw()
    with pytest.raises(tarot.TarotError):
        deck.draw()


def test_R2_draw_from_empty_deck_is_friendly_error(deck):
    with pytest.raises(tarot.TarotError):
        deck.draw()


def test_R2_shuffle_keeps_the_same_cards(deck):
    for i in range(20):
        deck.add("task {}".format(i))
    before = sorted(c["id"] for c in deck.cards)
    deck.shuffle()
    assert sorted(c["id"] for c in deck.cards) == before


def test_R2_flip_frames_are_all_the_same_size(plain_render):
    card = {"id": 7, "task": "write the report", "arcana": "The Dread"}
    frames = []
    for w in range(0, tarot.W + 1, 4):
        frames.append(tarot.compose(tarot.build_card(tarot.back_rows(), w)))
        frames.append(tarot.compose(tarot.build_card(tarot.face_rows(card), w)))
    for glow in (0, 0.3, 1):
        frames.append(tarot.card_frame(card, glow))
    assert len({len(f) for f in frames}) == 1
    assert len({tarot.visible_len(line) for f in frames for line in f}) == 1


def test_R2_glow_adds_a_halo(plain_render):
    card = {"id": 1, "task": "x", "arcana": "The Dread"}
    dark = "".join(tarot.card_frame(card, 0))
    lit = "".join(tarot.card_frame(card, 1))
    assert "▒" not in dark and "░" not in dark
    assert "▒" in lit and "░" in lit


# --- R3: whimsical, hardass message on each draw ---------------------------

def test_R3_message_pool_is_large_and_unique():
    assert len(tarot.FORTUNES) >= 30
    assert len(set(tarot.FORTUNES)) == len(tarot.FORTUNES)


def test_R3_draw_prints_a_message(deck_file, capsys, monkeypatch):
    monkeypatch.setenv("TAROT_DECK", deck_file)
    tarot.main(["--no-anim", "add", "x"])
    tarot.main(["--no-anim", "draw"])
    # The message is wrapped to sit under the card, so compare ignoring breaks.
    out = " ".join(capsys.readouterr().out.split())
    assert any(msg in out for msg in tarot.FORTUNES)


# --- R4: throw away a finished card ---------------------------------------

def test_R4_done_removes_card_for_good(deck, deck_file):
    deck.add("x")
    deck.add("y")
    drawn = deck.draw()
    deck.discard()
    deck.save()
    again = tarot.Deck(deck_file)
    assert drawn["id"] not in [c["id"] for c in again.all_cards()]
    assert [c["id"] for c in again.graveyard] == [drawn["id"]]


def test_R4_card_numbers_are_never_reused(deck):
    deck.add("x")
    deck.add("y")
    deck.discard(2)
    assert deck.add("z")["id"] == 3


def test_R4_done_by_number_works_for_deck_and_hand(deck):
    deck.add("x")
    deck.add("y")
    deck.discard(2)
    assert [c["id"] for c in deck.cards] == [1]
    deck.draw()
    deck.discard(1)
    assert deck.drawn is None and deck.cards == []


def test_R4_done_with_empty_hand_or_unknown_number_is_error(deck):
    deck.add("x")
    with pytest.raises(tarot.TarotError):
        deck.discard()
    with pytest.raises(tarot.TarotError):
        deck.discard(99)


def test_R4_card_numbers_accept_roman_numerals():
    assert tarot.parse_card_number("xiv") == 14
    assert tarot.parse_card_number(" 7 ") == 7
    with pytest.raises(tarot.TarotError):
        tarot.parse_card_number("banana")


# --- R5: striking cards ----------------------------------------------------

def test_R5_face_and_back_fill_the_card_exactly():
    card = {"id": 14, "task": "x", "arcana": "The Dread"}
    for rows in (tarot.face_rows(card), tarot.back_rows()):
        assert len(rows) == tarot.H
        assert all(len(text) == tarot.W for text, _, _ in rows)


def test_R5_face_shows_numeral_task_and_arcana():
    card = {"id": 14, "task": "feed the cat", "arcana": "The Dread"}
    text = "\n".join(t for t, _, _ in tarot.face_rows(card))
    assert "XIV" in text and "feed the cat" in text and "The Dread" in text


def test_R5_long_task_is_truncated_with_ellipsis():
    card = {"id": 1, "task": "word " * 100, "arcana": "The Dread"}
    rows = [t for t, _, _ in tarot.face_rows(card)]
    assert any("…" in r for r in rows)


def test_R5_back_has_medallion():
    text = "\n".join(t for t, _, _ in tarot.back_rows())
    assert "TAROT" in text and "OF  TASKS" in text


def test_R5_uses_truecolor_when_color_is_on(plain_render):
    line = tarot.card_frame({"id": 1, "task": "x", "arcana": "The Dread"})[3]
    assert "\x1b[38;2;" in line


def test_R5_roman_numerals():
    assert [tarot.roman(n) for n in (1, 4, 9, 14, 1994)] == [
        "I", "IV", "IX", "XIV", "MCMXCIV"]


# --- R6: return a drawn card ----------------------------------------------

def test_R6_return_puts_card_back_in_deck(deck):
    deck.add("x")
    card = deck.draw()
    assert deck.return_card() is card
    assert deck.drawn is None
    assert card in deck.cards


def test_R6_return_with_empty_hand_is_error(deck):
    with pytest.raises(tarot.TarotError):
        deck.return_card()


# --- End to end through the real script (R1-R7) ----------------------------

def run_cli(deck_file, *args, stdin=""):
    env = dict(os.environ, TAROT_DECK=deck_file, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "tarot.py"), *args],
        input=stdin.encode("utf-8"), capture_output=True, env=env, timeout=30)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode()


def test_R1_R2_R4_full_cycle_through_cli(deck_file):
    code, out, err = run_cli(deck_file, "add", "write the report", "buy cat food")
    assert code == 0, err
    assert out.count("sealed into the deck") == 2

    code, out, _ = run_cli(deck_file, "draw")
    assert code == 0
    assert "╔" in out
    assert "\x1b" not in out  # R5: no escape codes when piped

    code, out, _ = run_cli(deck_file, "draw")
    assert "already hold" in out

    code, out, _ = run_cli(deck_file, "done")
    assert code == 0 and "burns" in out

    with open(deck_file, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["cards"]) == 1
    assert data["drawn"] is None
    assert len(data["graveyard"]) == 1


def test_R7_errors_are_friendly_with_exit_code_1(deck_file):
    code, out, err = run_cli(deck_file, "done")
    assert code == 1
    assert "hand is empty" in out
    assert err == ""


def test_R1_R2_R4_interactive_menu(deck_file):
    code, out, err = run_cli(deck_file, stdin="a\nfeed the plants\n\nd\nf\nl\nq\n")
    assert code == 0, err
    assert "T A R O T" in out
    assert "feed the plants" in out
    assert "burns" in out
    assert "conquered" in out
