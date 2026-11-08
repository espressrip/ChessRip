import math
import os
import shutil
import stat
import sys
import time

import chess
import chess.engine

from .config import ROOT, save

BAD_SUFFIXES = {".txt", ".zip", ".md", ".tar", ".gz", ".json", ".nnue", ".html", ".py"}
MATE_CP = 10000      # tyle "centipionków" liczy się mat przy obliczaniu accuracy
MIN_DEPTH = 8        # płytsze iteracje ignorujemy (na głębokości 1-7 silnik wypluwa przypadkowe ruchy)


def _candidates(cfg):
    if cfg.get("stockfish_path"):
        yield cfg["stockfish_path"]
    if os.environ.get("STOCKFISH_PATH"):
        yield os.environ["STOCKFISH_PATH"]
    found = shutil.which("stockfish")
    if found:
        yield found
    # folder engine/ oraz folder z programem (exe wrzucony obok run.py)
    for folder, recursive in ((ROOT / "engine", True), (ROOT, False)):
        if folder.exists():
            files = folder.rglob("*") if recursive else folder.iterdir()
            for f in sorted(files):
                if f.is_file() and f.name.lower().startswith("stockfish") and f.suffix.lower() not in BAD_SUFFIXES:
                    yield str(f)


def _ask_path():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title="Wskaż plik wykonywalny Stockfisha")
        root.destroy()
        return path
    except Exception:
        return input("Podaj pełną ścieżkę do pliku Stockfisha: ").strip().strip('"')


def find_stockfish(cfg, force_dialog=False):
    if not force_dialog:
        for c in _candidates(cfg):
            if os.path.isfile(c):
                return c
    print("[engine] Nie znaleziono Stockfisha - wskaż plik.")
    path = _ask_path()
    if not path or not os.path.isfile(path):
        print("Nie podano poprawnej ścieżki. Zobacz README.md (sekcja 'Stockfish').")
        sys.exit(1)
    cfg["stockfish_path"] = path
    save(cfg)
    return path


def fmt_score(pov) -> str:
    s = pov.white()
    if s.is_mate():
        return f"#{s.mate()}"
    return f"{s.score() / 100:+.2f}"


def win_pct(cp: float) -> float:
    """Szansa na wygraną (0-100) z oceny w centipionkach - wzór jak w analizie chess.com/lichess."""
    cp = max(-1000.0, min(1000.0, cp))
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def accuracy(best_cp: float, move_cp: float) -> int:
    """Accuracy ruchu (0-100) względem najlepszego ruchu: im więcej szansy na wygraną tracisz, tym mniej."""
    diff = max(0.0, win_pct(best_cp) - win_pct(move_cp))
    acc = 103.1668 * math.exp(-0.04354 * diff) - 3.1669
    return int(round(max(0.0, min(100.0, acc))))


def _cp(info) -> int:
    return info["score"].relative.score(mate_score=MATE_CP)


class Engine:
    def __init__(self, cfg, force_dialog=False):
        path = find_stockfish(cfg, force_dialog)
        if os.name != "nt" and not os.access(path, os.X_OK):
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"[engine] Stockfish: {path}")
        self.engine = chess.engine.SimpleEngine.popen_uci(path)
        options = {
            "Threads": int(cfg["engine_threads"]),
            "Hash": int(cfg["engine_hash_mb"]),
            "Skill Level": int(cfg["skill_level"]),
        }
        for name, value in options.items():
            try:
                self.engine.configure({name: value})
            except Exception as e:
                print(f"[engine] Pominięto opcję {name}: {e}")
        self.think_time = float(cfg["think_time"])
        self.quick_time = min(float(cfg.get("quick_time", 0.3)), self.think_time)
        self.multipv = max(1, int(cfg["multipv"]))

    # ---------------------------------------------------------------- analiza
    def analyse(self, board: chess.Board, on_update=None):
        """Analiza "na żywo": po `quick_time` s oddaje pierwsze (wstępne) wyniki przez on_update(lines),
        potem odświeża je w miarę zwiększania głębokości, aż do `think_time` s.

        Accuracy każdego ruchu = jak bardzo ruch jest gorszy od najlepszego, liczone na NAJGŁĘBSZEJ
        osiągniętej głębokości. Ruch, który silnik wskazał po krótkim myśleniu, a głębsza analiza go
        obaliła, dostaje więc niską accuracy, a ruch znaleziony dopiero po dłuższym liczeniu - wysoką.
        """
        n_lines = min(self.multipv, board.legal_moves.count())
        if n_lines == 0:
            return []

        t0 = time.time()
        latest = {}          # multipv -> ostatnia informacja
        complete = None      # ostatni KOMPLETNY zestaw linii z jednej głębokości
        found = {}           # ruch -> po ilu sekundach pierwszy raz pojawił się na liście
        quick_best = None    # najlepszy ruch w chwili pierwszego "szybkiego" wyniku
        last_emit = 0.0

        with self.engine.analysis(board, chess.engine.Limit(time=self.think_time), multipv=n_lines) as analysis:
            for info in analysis:
                if not info.get("pv") or "multipv" not in info or "score" not in info:
                    continue
                if info.get("lowerbound") or info.get("upperbound"):
                    continue
                now = time.time() - t0
                latest[info["multipv"]] = info
                if info.get("depth", 0) >= MIN_DEPTH:
                    found.setdefault(info["pv"][0], now)
                if info["multipv"] != n_lines or len(latest) < n_lines:
                    continue

                complete = dict(latest)          # kompletna paczka linii z tej głębokości
                if now < self.quick_time or info.get("depth", 0) < MIN_DEPTH:
                    continue
                if quick_best is None:
                    quick_best = complete[1]["pv"][0]
                if on_update and now - last_emit >= 0.2:
                    last_emit = now
                    try:
                        on_update(self._lines(board, complete, found, quick_best))
                    except Exception as e:
                        print(f"[engine] Błąd odświeżania na żywo: {e}")

        if not complete:
            return []
        lines = self._lines(board, complete, found, quick_best)

        # Szybki typ, który głębsza analiza wypchnęła poza top-N: oceń go osobno, żeby pokazać jego (niską) accuracy
        if quick_best is not None and all(l["move"] != quick_best for l in lines):
            extra = self._probe(board, quick_best, lines[0]["cp"], found)
            if extra:
                lines.append(extra)
        return lines

    def _lines(self, board, complete, found, quick_best):
        infos = [complete[k] for k in sorted(complete)]
        best_cp = _cp(infos[0])
        lines = []
        for rank, info in enumerate(infos):
            mv = info["pv"][0]
            cp = _cp(info)
            lines.append({
                "move": mv,
                "san": board.san(mv),
                "score": fmt_score(info["score"]),
                "pv": board.variation_san(info["pv"][:6]),
                "cp": cp,
                "acc": accuracy(best_cp, cp),
                "depth": info.get("depth", 0),
                "found": found.get(mv, 0.0),
                "overturned": quick_best is not None and mv == quick_best and rank > 0,
            })
        return lines

    def _probe(self, board, move, best_cp, found):
        try:
            t = min(1.0, max(0.2, self.think_time * 0.4))
            info = self.engine.analyse(board, chess.engine.Limit(time=t), root_moves=[move])
            pv = info.get("pv") or [move]
            return {
                "move": move,
                "san": board.san(move),
                "score": fmt_score(info["score"]),
                "pv": board.variation_san(pv[:6]),
                "cp": _cp(info),
                "acc": accuracy(best_cp, _cp(info)),
                "depth": info.get("depth", 0),
                "found": found.get(move, 0.0),
                "overturned": True,
                "extra": True,
            }
        except Exception as e:
            print(f"[engine] Nie udało się ocenić szybkiego typu: {e}")
            return None

    def quit(self):
        try:
            self.engine.quit()
        except Exception:
            pass
