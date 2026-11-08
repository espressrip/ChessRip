"""Odczyt pozycji z DOM chess.com i zamiana na obiekt chess.Board."""
import re
from typing import Optional

import chess

READ_JS = """() => {
  const b = document.querySelector('wc-chess-board') || document.querySelector('chess-board');
  if (!b) return null;
  const r = b.getBoundingClientRect();
  return {
    pieces: Array.from(b.querySelectorAll('.piece')).map(e => String(e.className)),
    highlights: Array.from(b.querySelectorAll('.highlight')).map(e => String(e.className)),
    flipped: b.classList.contains('flipped'),
    w: r.width, h: r.height
  };
}"""

PIECE_RE = re.compile(r"\b([wb])([pnbrqk])\b")
SQ_RE = re.compile(r"square-(\d)(\d)")
START_PLACEMENT = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"


def parse_grid(state) -> dict:
    grid = {}
    for cls in state["pieces"]:
        p, s = PIECE_RE.search(cls), SQ_RE.search(cls)
        if not p or not s:
            continue
        sym = p.group(2).upper() if p.group(1) == "w" else p.group(2)
        grid[(int(s.group(1)) - 1, int(s.group(2)) - 1)] = sym
    return grid


def placement_fen(grid) -> str:
    rows = []
    for rank in range(7, -1, -1):
        row, empty = "", 0
        for f in range(8):
            p = grid.get((f, rank))
            if p is None:
                empty += 1
            else:
                if empty:
                    row += str(empty)
                    empty = 0
                row += p
        if empty:
            row += str(empty)
        rows.append(row)
    return "/".join(rows)


class CastleTracker:
    """Śledzi prawa do roszady: raz utracone nie wracają (do nowej partii)."""
    REQ = {
        "K": [((4, 0), "K"), ((7, 0), "R")],
        "Q": [((4, 0), "K"), ((0, 0), "R")],
        "k": [((4, 7), "k"), ((7, 7), "r")],
        "q": [((4, 7), "k"), ((0, 7), "r")],
    }

    def __init__(self):
        self.rights = set("KQkq")

    def update(self, grid, placement) -> str:
        if placement == START_PLACEMENT:
            self.rights = set("KQkq")
        for r in list(self.rights):
            if any(grid.get(sq) != piece for sq, piece in self.REQ[r]):
                self.rights.discard(r)
        return "".join(c for c in "KQkq" if c in self.rights) or "-"


def _guess_turn(grid, state) -> bool:
    """True = białe na ruchu. Strona, która ostatnio ruszyła, ma figurę na podświetlonym polu."""
    for cls in state["highlights"]:
        s = SQ_RE.search(cls)
        if not s:
            continue
        sym = grid.get((int(s.group(1)) - 1, int(s.group(2)) - 1))
        if sym:
            return not sym.isupper()
    return chess.WHITE


def build_board(state, tracker: CastleTracker) -> Optional[chess.Board]:
    grid = parse_grid(state)
    if not grid:
        return None
    placement = placement_fen(grid)
    castling = tracker.update(grid, placement)
    guess = _guess_turn(grid, state)
    for turn in (guess, not guess):
        fen = f"{placement} {'w' if turn else 'b'} {castling} - 0 1"
        try:
            board = chess.Board(fen)
        except ValueError:
            continue
        if board.is_valid():
            return board
    return None
