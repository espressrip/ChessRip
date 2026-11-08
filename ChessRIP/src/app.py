import argparse
import os
import sys
import time
from pathlib import Path

import chess

from . import config as config_mod
from . import browsers, overlay
from .board_reader import READ_JS, CastleTracker, build_board
from .engine import Engine

ROOT = Path(__file__).resolve().parent.parent


def wait_for_board(page, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        try:
            state = page.evaluate(READ_JS)
        except Exception:
            state = None
        if state and state["pieces"]:
            return state
        time.sleep(1)
    return None


def print_report(board, lines):
    side = "białe" if board.turn else "czarne"
    print(f"\n--- Ruch {board.fullmove_number}, na ruchu: {side} ---")
    for i, l in enumerate(lines, 1):
        note = ""
        if l.get("extra"):
            note = "  <- szybki typ, obalony głębiej (niebieska przerywana)"
        elif l.get("overturned"):
            note = "  <- szybki typ, obalony głębiej"
        mark = "*" if l.get("extra") else str(i)
        print(f" {mark}. {l['san']:<8} {l['score']:>7}  acc {l['acc']:>3}%  gł.{l['depth']:<2} "
              f"({l['found']:.1f}s)  {l['pv']}{note}")


def calibrate(page, cfg):
    print("Otwórz partię z botem. Czekam na szachownicę (do 5 min)...")
    state = wait_for_board(page)
    if not state:
        print("Nie wykryto szachownicy.")
        return
    side = "czarnymi" if state["flipped"] else "białymi"
    print(f"Wykryto szachownicę {state['w']:.0f}x{state['h']:.0f}px, grasz {side}.")
    print("Przez 10 s zobaczysz czerwoną ramkę, znaczniki a1/h8 i trzy testowe strzałki z accuracy.")
    print("Jeśli a1 jest w prawym górnym rogu, a h8 w lewym dolnym - to normalne dla gry czarnymi.")
    test = overlay.make_arrows(
        [{"move": chess.Move.from_uci("e2e4"), "acc": 100},
         {"move": chess.Move.from_uci("d2d4"), "acc": 87},
         {"move": chess.Move.from_uci("g1f3"), "acc": 64}],
        cfg["arrow_colors"], cfg["quick_pick_color"], cfg["show_accuracy"])
    end = time.time() + 10
    while time.time() < end:
        overlay.draw(page, test, calibrate=True)
        time.sleep(0.5)
    overlay.clear(page)
    print("Kalibracja zakończona - znaczniki są na właściwych rogach? Jeśli tak, wszystko działa.")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Stockfish + chess.com (trening z botami)")
    ap.add_argument("--calibrate", action="store_true", help="test dopasowania strzałek do szachownicy")
    ap.add_argument("--setup", action="store_true", help="ponownie wskaż plik Stockfisha")
    ap.add_argument("--browser", choices=browsers.ALL, help="przeglądarka (domyślnie ta z BROWSER w run.py)")
    ap.add_argument("--no-arrows", action="store_true", help="tylko konsola, bez strzałek")
    args = ap.parse_args()

    cfg = config_mod.load()
    if args.no_arrows:
        cfg["show_arrows"] = False

    engine = None
    if not args.calibrate:
        engine = Engine(cfg, force_dialog=args.setup)

    name = (args.browser or os.environ.get("CST_BROWSER") or cfg.get("browser") or "chrome").lower().strip()
    if name not in browsers.ALL:
        print(f"Nieznana przeglądarka '{name}'. Dostępne: {', '.join(browsers.ALL)}")
        sys.exit(1)

    driver = None
    try:
        if name == "firefox":
            driver, page = browsers.open_firefox(cfg)
            run(page, cfg, engine, args)
        else:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                page = browsers.open_chromium(p, name, cfg)
                run(page, cfg, engine, args)
    except KeyboardInterrupt:
        print("\nZatrzymano.")
    finally:
        if engine:
            engine.quit()
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def run(page, cfg, engine, args):
    if args.calibrate:
        calibrate(page, cfg)
    else:
        loop(page, cfg, engine)


def loop(page, cfg, engine):
    print("\nOtwórz partię z botem na chess.com (Graj -> Komputer). Strzałki: F2 ukrywa/pokazuje.")
    tracker = CastleTracker()
    last_fen = candidate = None
    pending = None
    shown = []

    while True:
        try:
            state = page.evaluate(READ_JS)
        except Exception:
            if page.is_closed():
                print("Karta została zamknięta - kończę.")
                return
            time.sleep(1)
            continue

        if not state or not state["pieces"]:
            if last_fen:
                print("Brak szachownicy - czekam na partię...")
            last_fen = candidate = pending = None
            shown = []
            time.sleep(1)
            continue

        board = build_board(state, tracker)
        if board is None:
            time.sleep(cfg["poll_interval"])
            continue

        fen = board.fen()
        if fen != last_fen:
            if fen != candidate:          # pozycja musi być stabilna przez dwa odczyty
                candidate = fen
                time.sleep(cfg["poll_interval"])
                continue
            last_fen = fen
            pending, shown = None, []
            try:
                overlay.clear(page)
            except Exception:
                pass

            my_color = chess.BLACK if state["flipped"] else chess.WHITE
            if board.is_game_over():
                print(f"\nKoniec partii: {board.result()}")
            elif cfg["only_my_turn"] and board.turn != my_color:
                print("\nRuch przeciwnika (bota)...")
            else:
                live = cfg["show_arrows"] and float(cfg["hint_delay"]) <= 0

                def on_update(partial, _page=page):
                    # wstępne strzałki w trakcie liczenia (wyblakłe, accuracy z "~"), odświeżane z każdą głębokością
                    overlay.draw(_page, overlay.make_arrows(
                        partial, cfg["arrow_colors"], cfg["quick_pick_color"],
                        cfg["show_accuracy"], provisional=True))

                lines = engine.analyse(board, on_update if live else None)
                print_report(board, lines)
                if cfg["show_arrows"] and lines:
                    pending = {
                        "due": time.time() + float(cfg["hint_delay"]),
                        "arrows": overlay.make_arrows(
                            lines, cfg["arrow_colors"], cfg["quick_pick_color"], cfg["show_accuracy"]),
                    }

        if pending and time.time() >= pending["due"]:
            shown, pending = pending["arrows"], None
        if shown:
            try:
                overlay.draw(page, shown)    # ponowne wstrzyknięcie, gdyby strona przerysowała planszę
            except Exception:
                pass

        time.sleep(cfg["poll_interval"])


if __name__ == "__main__":
    main()
