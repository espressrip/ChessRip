#!/usr/bin/env python3
"""Launcher: installs libraries in python"""

# ============================================================================
# >>> HERE CHANGE TO YOUR BROWSER:  "chrome", "brave", "opera", "opera_gx", "edge" albo "firefox"
BROWSER = "type here"
# ============================================================================

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
CHILD_FLAG = "CST_CHILD"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def has_pip(py) -> bool:
    return subprocess.run([str(py), "-m", "pip", "--version"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def make_venv():
    """Zwraca python z działającym pip-em w .venv albo None."""
    try:
        if not venv_python().exists():
            print("[setup] Tworzę wirtualne środowisko (.venv)...")
            venv.create(VENV, with_pip=True)
        py = venv_python()
        if not has_pip(py):
            subprocess.call([str(py), "-m", "ensurepip", "--upgrade"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if has_pip(py):
            return py
    except Exception as e:
        print(f"[setup] Problem z .venv: {e}")
    shutil.rmtree(VENV, ignore_errors=True)       # zepsute środowisko bez pip-a - kasujemy
    return None


def needed_modules(browser: str):
    return ["chess", "selenium"] if browser == "firefox" else ["chess", "playwright"]


def bootstrap() -> int:
    if sys.version_info < (3, 9):
        print("Wymagany Python 3.9 lub nowszy.")
        return 1
    browser = (os.environ.get("CST_BROWSER") or BROWSER).lower().strip()
    mods = needed_modules(browser)
    reqs = [str(ROOT / "requirements.txt")]
    extra = ["selenium>=4.20"] if browser == "firefox" else []

    py = make_venv()
    user_flag = []
    if py is None:
        print("[setup] .venv bez pip-a nie działa - instaluję w zwykłym Pythonie (pip --user).")
        py = Path(sys.executable)
        user_flag = ["--user"]
        if not has_pip(py):
            subprocess.call([str(py), "-m", "ensurepip", "--upgrade"])
        if not has_pip(py):
            print("Ten Python nie ma pip-a. Zainstaluj Pythona z python.org (z opcją pip) i spróbuj ponownie.")
            return 1

    check = subprocess.run([str(py), "-c", "import " + ", ".join(mods)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if check.returncode != 0:
        print("[setup] Instaluję biblioteki...")
        cmd = [str(py), "-m", "pip", "install", *user_flag, "-r", reqs[0], *extra]
        if subprocess.call(cmd) != 0:
            print("Instalacja bibliotek nie powiodła się (sprawdź internet). Ręcznie: "
                  f"{py} -m pip install -r requirements.txt")
            return 1

    env = dict(os.environ, **{CHILD_FLAG: "1", "CST_BROWSER": browser})
    return subprocess.call([str(py), str(Path(__file__).resolve()), *sys.argv[1:]], env=env)


if __name__ == "__main__":
    if os.environ.get(CHILD_FLAG) == "1":
        sys.path.insert(0, str(ROOT))
        from src.app import main
        main()
    else:
        sys.exit(bootstrap())
