"""Otwieranie ISTNIEJĄCEJ przeglądarki użytkownika (bez pobierania nowej).

Chrome / Brave / Opera / Edge (Chromium): uruchamiamy zainstalowaną przeglądarkę z portem debugowania
i podpinamy się przez CDP (Playwright). Używa osobnego profilu w folderze programu - zaloguj się
na chess.com tylko raz, kolejne starty pamiętają logowanie.
Firefox: Playwright nie umie sterować zwykłym Firefoxem, więc używamy Selenium (geckodriver
pobiera się sam przy pierwszym uruchomieniu).
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROMIUM_BASED = ("chrome", "brave", "opera", "opera_gx", "edge")
ALL = CHROMIUM_BASED + ("firefox",)


def _win_paths(name):
    pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    la = os.environ.get("LOCALAPPDATA", "")
    rel = {
        "chrome": [r"Google\Chrome\Application\chrome.exe"],
        "brave": [r"BraveSoftware\Brave-Browser\Application\brave.exe"],
        "edge": [r"Microsoft\Edge\Application\msedge.exe"],
        "opera": [r"Opera\opera.exe", r"Opera\launcher.exe"],
        "opera_gx": [r"Opera GX\opera.exe", r"Opera GX\launcher.exe"],
    }[name]
    bases = [pf, pf86, la, os.path.join(la, "Programs")] if la else [pf, pf86]
    out = [os.path.join(b, r) for b in bases for r in rel]
    return out


def find_browser(name):
    if sys.platform.startswith("win"):
        cands = _win_paths(name)
    elif sys.platform == "darwin":
        cands = {
            "chrome": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
            "brave": ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"],
            "edge": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
            "opera": ["/Applications/Opera.app/Contents/MacOS/Opera"],
            "opera_gx": ["/Applications/Opera GX.app/Contents/MacOS/Opera"],
        }[name]
    else:
        names = {
            "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
            "brave": ["brave-browser", "brave"],
            "edge": ["microsoft-edge", "microsoft-edge-stable"],
            "opera": ["opera"],
            "opera_gx": ["opera"],
        }[name]
        cands = [shutil.which(n) for n in names]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def _port_open(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as r:
            json.load(r)
        return True
    except Exception:
        return False


def open_chromium(p, name, cfg):
    port = int(cfg.get("cdp_port", 9222))
    if not _port_open(port):
        exe = find_browser(name)
        if not exe:
            print(f"Nie znaleziono przeglądarki '{name}'. Zainstaluj ją albo zmień BROWSER na górze run.py "
                  f"(dostępne: {', '.join(ALL)}).")
            sys.exit(1)
        profile = ROOT / f"profile_{name}"
        profile.mkdir(exist_ok=True)
        print(f"[browser] Uruchamiam {name}: {exe}")
        subprocess.Popen([
            exe, f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
            "--start-maximized", "--no-first-run", "--no-default-browser-check", cfg["start_url"],
        ])
        for _ in range(60):
            if _port_open(port):
                break
            time.sleep(0.5)
        else:
            print(f"Przeglądarka nie otworzyła portu {port}. Zamknij wszystkie okna '{name}' z tego profilu i spróbuj ponownie.")
            sys.exit(1)
    else:
        print(f"[browser] Port {port} już działa - podpinam się pod otwartą przeglądarkę.")

    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    print("[browser] Czekam na kartę z chess.com...")
    opened = False
    while True:
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if "chess.com" in pg.url:
                    return pg
        if not opened:
            opened = True
            try:
                ctx = browser.contexts[0]
                pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                pg.goto(cfg["start_url"])
            except Exception:
                pass
        time.sleep(1)


class SeleniumPage:
    """Minimalna nakładka, żeby reszta programu mogła wołać page.evaluate(js, arg) jak w Playwright."""

    def __init__(self, driver):
        self.driver = driver

    def evaluate(self, js, arg=None):
        if arg is None:
            return self.driver.execute_script(f"return ({js})();")
        return self.driver.execute_script(f"return ({js})(arguments[0]);", arg)

    def is_closed(self):
        try:
            return not self.driver.window_handles
        except Exception:
            return True


def open_firefox(cfg):
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
    except ImportError:
        print("Brak biblioteki selenium (dla Firefoxa). Uruchom ponownie przez: python run.py")
        sys.exit(1)
    profile = ROOT / "profile_firefox"
    profile.mkdir(exist_ok=True)
    opts = Options()
    opts.add_argument("-profile")
    opts.add_argument(str(profile))
    print("[browser] Uruchamiam Firefoxa (przy 1. starcie Selenium pobierze geckodriver)...")
    driver = webdriver.Firefox(options=opts)
    try:
        driver.maximize_window()
    except Exception:
        pass
    driver.get(cfg["start_url"])
    return driver, SeleniumPage(driver)
