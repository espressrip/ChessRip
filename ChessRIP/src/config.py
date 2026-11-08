import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"

DEFAULTS = {
    "cdp_port": 9222,              # port debugowania przeglądarki (Chrome/Brave/Opera/Edge)
    "start_url": "https://www.chess.com/play/computer",
    "stockfish_path": "",
    "engine_threads": 2,
    "engine_hash_mb": 256,
    "think_time": 1.5,             # maks. czas analizy (s) - im dłużej, tym pewniejsze accuracy
    "quick_time": 0.3,             # po tylu sekundach pokazują się pierwsze, wstępne strzałki
    "multipv": 5,
    "skill_level": 20,             # 0-20, siła podpowiedzi
    "only_my_turn": True,
    "hint_delay": 0,               # sekundy zwłoki przed pokazaniem strzałek (trening: najpierw pomyśl sam)
    "show_arrows": True,
    "show_accuracy": True,         # etykieta z accuracy na każdej strzałce
    "quick_pick_color": "#60a5fa", # kolor przerywanej strzałki "szybkiego typu" obalonego głębszą analizą
    "poll_interval": 0.3,
    "arrow_colors": ["#22c55e", "#eab308", "#f97316", "#ef4444", "#a855f7"],
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[config] Błąd w config.json ({e}) - używam ustawień domyślnych.")
    return cfg


def save(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
