# Stockfish + chess.com – trening z botami

Program łączy silnik **Stockfish** z kartą przeglądarki z **chess.com**. Czyta pozycję
z szachownicy, liczy najlepsze ruchy i rysuje **strzałki podpowiedzi bezpośrednio na planszy**
(zielona = najlepszy ruch, żółta i pomarańczowa = kolejne). Na każdej strzałce jest
**accuracy** (0–100%), a w konsoli dostajesz ocenę pozycji i główne warianty.

> ⚠️ **Używaj wyłącznie do gry z botami (Graj → Komputer) i analizy własnych partii.**
> Korzystanie z silnika w grach z żywymi ludźmi łamie zasady Fair Play chess.com
> i kończy się banem konta.

## Wymagania

- Python **3.9+** (https://www.python.org/downloads/ – na Windows zaznacz „Add Python to PATH")
- Połączenie z internetem przy pierwszym uruchomieniu (biblioteki)
- Konto na chess.com (darmowe wystarczy)

## Szybki start

1. Rozpakuj ZIP-a.
2. Pobierz Stockfisha (sekcja niżej) i wrzuć go do folderu `engine/`.
3. W terminalu, w folderze projektu:

   ```
   python run.py
   ```
   (na Linux/macOS: `python3 run.py`)

   Przy pierwszym starcie skrypt **sam** zainstaluje `python-chess` i `playwright` (w `.venv`, a gdy pip tam
   nie działa – w zwykłym Pythonie). Kolejne starty są natychmiastowe.
4. Otworzy się Twoja zainstalowana przeglądarka (wybierasz ją w `BROWSER` na górze `run.py`). Zaloguj się na chess.com i zacznij partię: **Graj → Komputer → wybierz bota**.
5. Gdy będzie Twój ruch, w konsoli pojawią się propozycje, a na szachownicy strzałki.

## Stockfish – jak go podłączyć

1. Wejdź na **https://stockfishchess.org/download/** i pobierz wersję dla swojego systemu.
   Dla większości nowoczesnych komputerów (Windows/Linux) wybierz wariant **avx2**
   (jeśli się nie uruchamia – wariant bez avx2 / „sse41-popcnt"). Na Macu: wersja `apple-silicon` (M1/M2/M3…) lub `x86-64`.
2. Rozpakuj archiwum.
3. Podłącz silnik **jedną** z metod:

   | Metoda | Co zrobić |
   |---|---|
   | **A. Folder `engine/`** (najprostsza) | Skopiuj plik wykonywalny (np. `stockfish-windows-x86-64-avx2.exe`) do folderu `engine/`. Nazwa musi zaczynać się od `stockfish`. Program znajdzie go sam. |
   | **B. config.json** | Wpisz pełną ścieżkę w `"stockfish_path"`, np. `"C:/Tools/stockfish/stockfish.exe"` (używaj `/` lub `\\`). |
   | **C. Zmienna systemowa** | Ustaw `STOCKFISH_PATH` lub dodaj Stockfisha do `PATH` (np. `brew install stockfish`, `sudo apt install stockfish`). |
   | **D. Okno wyboru** | Jeśli nic nie znajdzie, program otworzy okno wyboru pliku i zapamięta ścieżkę. Wymuszenie: `python run.py --setup`. |

4. Linux/macOS: program sam nadaje plikowi prawo wykonywania. Gdyby nie zadziałało: `chmod +x engine/stockfish*`.
   Na macOS przy komunikacie o zablokowaniu pliku: *Ustawienia → Prywatność i ochrona → Zezwól*.

## Accuracy na strzałkach

Stockfish liczy w kilku krokach, więc strzałki pojawiają się **na żywo**:

1. Po `quick_time` (domyślnie 0,3 s) rysują się **wstępne** strzałki – wyblakłe, z accuracy w stylu `~96%`.
2. W miarę jak silnik schodzi głębiej, strzałki i procenty się odświeżają (maks. do `think_time`).
3. Po zakończeniu liczenia strzałki robią się pełne, a accuracy jest **ostateczna**.

Accuracy ruchu = jak dużo szans na wygraną tracisz względem najlepszego ruchu, liczone na **najgłębszej**
osiągniętej głębokości (wzór jak w analizie chess.com; najlepszy ruch = 100%).

Dzięki temu ruch, który Stockfish wymyślił po krótkim myśleniu, a głębsza analiza go obaliła, ma **niską
accuracy**, a ruch znaleziony dopiero po dłuższym liczeniu – **wysoką**. Taki obalony „szybki typ” jest
dodatkowo rysowany **niebieską przerywaną strzałką** (jeśli wypadł z top-N), żebyś widział, jak bardzo się
mylił. W konsoli przy każdym ruchu jest też głębokość i czas, po którym się pojawił.

Wyłączenie etykiet: `"show_accuracy": false`. Dłuższe myślenie = pewniejsze wyniki: zwiększ `think_time`.

## Kalibracja szachownicy (strzałki)

Kalibracja jest **automatyczna**: strzałki są rysowane jako warstwa SVG wewnątrz elementu
szachownicy, więc skalują się razem z planszą (zmiana rozmiaru okna, zoom, odwrócenie planszy
przy grze czarnymi – wszystko działa bez ręcznego ustawiania rogów).

Test dopasowania:

```
python run.py --calibrate
```

Otwórz partię; przez 10 s zobaczysz czerwoną ramkę dookoła planszy, znaczniki **a1** i **h8**
oraz testową strzałkę e2→e4. Jeśli znaczniki leżą na właściwych rogach (a1 w lewym dolnym przy
grze białymi, w prawym górnym przy czarnych) – wszystko jest skalibrowane.

Opcje:
- `--no-arrows` – tylko podpowiedzi w konsoli, bez rysowania,
- klawisz **F2** w przeglądarce – ukryj/pokaż strzałki w trakcie gry,
- `"show_arrows": false` w `config.json` – wyłącza strzałki na stałe.

## Wybór przeglądarki

Na samej górze `run.py` jest linijka:

```python
BROWSER = "chrome"   # "chrome", "brave", "opera", "opera_gx", "edge" albo "firefox"
```

Zmień nazwę i odpal ponownie (albo jednorazowo: `python run.py --browser brave`). Program **nie pobiera
żadnej przeglądarki** – otwiera tę zainstalowaną u Ciebie, w osobnym profilu (`profile_<nazwa>/` w folderze
programu), więc na chess.com logujesz się tylko raz. Chromium-owe przeglądarki podpinamy przez port
debugowania 9222; jeśli okno nie chce się otworzyć, zamknij wszystkie okna tej przeglądarki i spróbuj znowu.
Firefox działa przez Selenium (geckodriver pobiera się sam przy pierwszym starcie).

## Ustawienia (`config.json`)

| Klucz | Znaczenie |
|---|---|
| `cdp_port` | port debugowania dla Chrome/Brave/Opera/Edge (domyślnie 9222) |
| `stockfish_path` | ścieżka do silnika (puste = autowykrywanie) |
| `think_time` | maksymalny czas analizy ruchu w sekundach (1–3 zwykle wystarcza) |
| `quick_time` | po ilu sekundach pokazać pierwsze, wstępne strzałki |
| `show_accuracy` | etykieta z accuracy na strzałkach |
| `quick_pick_color` | kolor przerywanej strzałki obalonego „szybkiego typu” |
| `multipv` | ile ruchów pokazywać (domyślnie 5: trzy najlepsze + dwa słabsze z niższą accuracy; tyle kolorów musi być w `arrow_colors`) |
| `skill_level` | 0–20; niższa wartość = słabsze, „bardziej ludzkie" podpowiedzi |
| `hint_delay` | sekundy zwłoki przed pokazaniem strzałek – **świetne do treningu**: najpierw myślisz sam, potem sprawdzasz |
| `only_my_turn` | podpowiedzi tylko, gdy Twoja kolej |
| `engine_threads`, `engine_hash_mb` | wydajność silnika |
| `arrow_colors` | kolory kolejnych strzałek |
| `poll_interval` | jak często odczytywać planszę (s) |

## Jak to działa

1. Playwright (lub Selenium w Firefoxie) odczytuje z DOM chess.com rozmieszczenie figur (`wc-chess-board`) i orientację planszy.
2. Strona na ruchu jest wykrywana z podświetlenia ostatniego ruchu, prawa do roszady są śledzone w trakcie partii.
3. Pozycja trafia jako FEN do Stockfisha (przez `python-chess`).
4. Wynik wraca do przeglądarki jako strzałki SVG nad planszą.

## Rozwiązywanie problemów

- **„Nie znaleziono Stockfisha"** – patrz sekcja *Stockfish*, metoda A lub D.
- **Stockfish zamyka się / błąd uruchomienia** – pobierz wariant bez `avx2` (starszy procesor).
- **Okno przeglądarki nie zajmuje całego ekranu (strona w małym prostokącie)** – naprawione (`no_viewport=True`
  w `src/app.py`). Jeśli masz jeszcze stary `browser_profile/`, możesz go usunąć.
- **Brak strzałek, ale ruchy w konsoli są** – uruchom `--calibrate`; sprawdź czy F2 nie ukrył warstwy.
- **„Czekam na szachownicę"** – otwórz właściwą partię (Graj → Komputer); działa też w widoku analizy/przeglądu partii.
- **Dziwne podpowiedzi roszady po dołączeniu w środku partii** – program zakłada, że prawa do roszady
  istnieją, dopóki nie zobaczy ruchu króla/wieży. Najdokładniej działa, gdy uruchomisz go przed pierwszym ruchem.
- **Chess.com zmienił strukturę strony** – selektory są w `src/board_reader.py` (`READ_JS`) i `src/overlay.py`.
- **Reset środowiska** – usuń folder `.venv` i uruchom `python run.py` ponownie.
- **„No module named pip"** – naprawione: launcher sam naprawia/omija zepsute `.venv`. Stary folder `.venv` możesz usunąć.

## Struktura projektu

```
run.py              launcher + automatyczna instalacja bibliotek
src/browsers.py     uruchamianie zainstalowanej przeglądarki
config.json         ustawienia
engine/             tu wrzucasz Stockfisha
src/app.py          pętla główna, CLI
src/engine.py       obsługa Stockfisha
src/board_reader.py odczyt pozycji z chess.com
src/overlay.py      strzałki / kalibracja
```
