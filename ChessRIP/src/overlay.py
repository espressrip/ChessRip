"""Rysowanie strzałek jako SVG wstrzykniętego w element szachownicy.

Kalibracja jest automatyczna: SVG ma viewBox 800x800 i rozciąga się na całą planszę,
więc działa przy dowolnym rozmiarze okna, zoomie i odwróceniu szachownicy.
Klawisz F2 w przeglądarce ukrywa/pokazuje strzałki.
"""

OVERLAY_JS = """(args) => {
  const b = document.querySelector('wc-chess-board') || document.querySelector('chess-board');
  if (!b) return false;
  const NS = 'http://www.w3.org/2000/svg';
  if (getComputedStyle(b).position === 'static') b.style.position = 'relative';

  let svg = b.querySelector('#cst-overlay');
  if (!svg) {
    svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('id', 'cst-overlay');
    svg.setAttribute('viewBox', '0 0 800 800');
    svg.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:60;';
    b.appendChild(svg);
  }
  if (!window.__cstKeys) {
    window.__cstKeys = true;
    window.__cstHidden = false;
    window.addEventListener('keydown', (e) => {
      if (e.key === 'F2') {
        window.__cstHidden = !window.__cstHidden;
        const s = document.querySelector('#cst-overlay');
        if (s) s.style.display = window.__cstHidden ? 'none' : '';
      }
    });
  }
  svg.style.display = window.__cstHidden ? 'none' : '';

  const flipped = b.classList.contains('flipped');
  const sig = JSON.stringify([args, flipped]);
  if (svg.dataset.sig === sig) return true;
  svg.dataset.sig = sig;
  while (svg.firstChild) svg.removeChild(svg.firstChild);

  const S = 100;
  const ctr = (f, r) => [(flipped ? 7 - f : f) * S + S / 2, (flipped ? r : 7 - r) * S + S / 2];
  const el = (name, attrs) => {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  };

  if (args.calibrate) {
    svg.appendChild(el('rect', {x: 3, y: 3, width: 794, height: 794, fill: 'none', stroke: '#ef4444', 'stroke-width': 6}));
    const marks = [[0, 0, 'a1'], [7, 7, 'h8']];
    for (const [f, r, label] of marks) {
      const [cx, cy] = ctr(f, r);
      svg.appendChild(el('circle', {cx, cy, r: 38, fill: '#ef4444', opacity: 0.85}));
      const t = el('text', {x: cx, y: cy + 9, 'text-anchor': 'middle', fill: '#fff', 'font-size': 28, 'font-weight': 'bold'});
      t.textContent = label;
      svg.appendChild(t);
    }
  }

  const labels = [];
  for (const a of args.arrows) {
    const [x1, y1] = ctr(a.from[0], a.from[1]);
    const [x2, y2] = ctr(a.to[0], a.to[1]);
    const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy) || 1;
    const ux = dx / len, uy = dy / len, px = -uy, py = ux;
    const head = 46, half = 32;
    const g = el('g', {opacity: a.opacity});
    const lineAttrs = {
      x1: x1 + ux * 22, y1: y1 + uy * 22,
      x2: x2 - ux * (head - 4), y2: y2 - uy * (head - 4),
      stroke: a.color, 'stroke-width': a.width
    };
    if (a.dash) lineAttrs['stroke-dasharray'] = '22 14';
    g.appendChild(el('line', lineAttrs));
    const tip = [x2 - ux * 6, y2 - uy * 6];
    const bx = x2 - ux * (head + 6), by = y2 - uy * (head + 6);
    const pts = [tip, [bx + px * half, by + py * half], [bx - px * half, by - py * half]]
      .map(p => p.join(',')).join(' ');
    g.appendChild(el('polygon', {points: pts, fill: a.color}));
    svg.appendChild(g);
    if (a.label) {
      // etykieta leży na strzałce tuż za grotem (przy krótkich - w połowie)
      const back = Math.min(len * 0.5, 100);
      labels.push({a, x: x2 - ux * back, y: y2 - uy * back, px, py});
    }
  }

  // etykiety accuracy rysujemy na wierzchu; gdy dwie na siebie nachodzą, przesuwamy je w bok
  const placed = [];
  const W = 92, H = 44;
  for (const L of labels) {
    let cx = L.x, cy = L.y;
    for (const off of [0, 48, -48, 96, -96]) {
      const tx = L.x + L.px * off, ty = L.y + L.py * off;
      if (!placed.some(q => Math.abs(q[0] - tx) < W && Math.abs(q[1] - ty) < H)) { cx = tx; cy = ty; break; }
    }
    cx = Math.max(W / 2, Math.min(800 - W / 2, cx));
    cy = Math.max(H / 2, Math.min(800 - H / 2, cy));
    placed.push([cx, cy]);
    const g = el('g', {opacity: L.a.label_opacity});
    g.appendChild(el('rect', {
      x: cx - W / 2, y: cy - H / 2, width: W, height: H, rx: 12,
      fill: '#0f172a', 'fill-opacity': 0.9, stroke: L.a.color, 'stroke-width': 4
    }));
    const t = el('text', {
      x: cx, y: cy + 10, 'text-anchor': 'middle', fill: '#ffffff',
      'font-size': 30, 'font-weight': 'bold', 'font-family': 'Arial, sans-serif'
    });
    t.textContent = L.a.label;
    g.appendChild(t);
    svg.appendChild(g);
  }
  return true;
}"""


def draw(page, arrows, calibrate=False) -> bool:
    return page.evaluate(OVERLAY_JS, {"arrows": arrows, "calibrate": calibrate})


def clear(page) -> bool:
    return draw(page, [])


def make_arrows(lines, colors, quick_color="#60a5fa", show_accuracy=True, provisional=False):
    """Zamienia linie z silnika na strzałki.

    provisional=True - wstępne wyniki w trakcie liczenia (strzałki i etykiety są wyblakłe, a accuracy
    ma przedrostek "~"); po zakończeniu analizy rysujemy je ponownie już na stałe.
    Linia z kluczem "extra" to szybki typ obalony przez głębszą analizę - rysowany przerywaną
    strzałką w kolorze quick_color.
    """
    import chess
    arrows = []
    main = [l for l in lines if not l.get("extra")]
    extra = [l for l in lines if l.get("extra")]
    plan = [(l, colors[i], False) for i, l in enumerate(main[: len(colors)])]
    plan += [(l, quick_color, True) for l in extra]
    for i, (line, color, dash) in enumerate(plan):
        m = line["move"]
        label = None
        if show_accuracy and line.get("acc") is not None:
            label = f"{'~' if provisional else ''}{line['acc']}%"
        arrows.append({
            "from": [chess.square_file(m.from_square), chess.square_rank(m.from_square)],
            "to": [chess.square_file(m.to_square), chess.square_rank(m.to_square)],
            "color": color,
            "opacity": (0.85 if i == 0 else 0.55 if i < 3 else 0.42) * (0.7 if provisional else 1.0),
            "label_opacity": 0.75 if provisional else 1.0,
            "width": 18 if i == 0 else 12 if i < 3 else 9,
            "dash": dash,
            "label": label,
        })
    return arrows
