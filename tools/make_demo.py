"""Renders a captioned demo video of Lucent without a screen recorder.

It drives the *real* Lucent widgets (Hub, overlays, splash, PDF/text viewers)
offscreen, composites them over drawn mock desktops, adds captions and key
badges, and pipes the frames to ffmpeg.

    QT_QPA_PLATFORM=offscreen python tools/make_demo.py demo.mp4
    QT_QPA_PLATFORM=offscreen python tools/make_demo.py --preview 3,25,41  # PNGs only

Caveat: this is a simulation. The "desktop" behind the overlays is drawn, and
the transparency is composited, so it shows what Lucent looks like, not a
capture of a live machine.
"""
import math
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

from PySide6.QtCore import QCoreApplication, QPointF, QRect, QRectF, Qt  # noqa: E402

QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

from PySide6.QtGui import (QBrush, QColor, QFont, QImage, QLinearGradient,  # noqa: E402
                           QPageSize, QPainter, QPdfWriter, QPen, QPixmap,
                           QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QApplication  # noqa: E402

W, H, FPS = 1280, 720, 24
WORK = "/tmp/lucent_demo"


# ------------------------------------------------------------------ helpers
def clamp(x):
    return max(0.0, min(1.0, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def font(px, bold=False, mono=False):
    from lucent import theme
    f = theme.mono_font(10) if mono else theme.ui_font(10)
    f.setPixelSize(px)
    f.setBold(bold)
    return f


def fade_window(t, dur, fin=0.4, fout=0.4):
    return min(smooth(t / fin), smooth((dur - t) / fout))


def caption(p, text, t, dur, y=H - 118):
    a = fade_window(t, dur)
    if a <= 0:
        return
    p.save()
    p.setOpacity(a)
    p.setFont(font(26, bold=True))
    r = p.fontMetrics().boundingRect(QRect(0, 0, 1040, 300), Qt.TextWordWrap | Qt.AlignCenter, text)
    pill = QRectF((W - r.width()) / 2 - 28, y - r.height() / 2 - 14, r.width() + 56, r.height() + 28)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(8, 12, 20, 205))
    p.drawRoundedRect(pill, 14, 14)
    p.setPen(QColor("#ffffff"))
    p.drawText(pill, Qt.AlignCenter | Qt.TextWordWrap, text)
    p.restore()


def keycap(p, label, t, start, dur=2.2, y=H - 205, cx=W / 2):
    """Key badge that pops in at `start` and lingers for `dur`."""
    lt = t - start
    if lt < 0 or lt > dur:
        return
    a = min(smooth(lt / 0.15), smooth((dur - lt) / 0.4))
    press = 1 - smooth(lt / 0.25) * 0.0
    p.save()
    p.setOpacity(a)
    p.setFont(font(24, bold=True))
    r = p.fontMetrics().boundingRect(label)
    box = QRectF(cx - r.width() / 2 - 22, y - 24, r.width() + 44, 48)
    p.setPen(QPen(QColor(255, 255, 255, 120), 2))
    p.setBrush(QColor(30, 40, 60, 235))
    p.drawRoundedRect(box, 9, 9)
    p.setPen(QColor("#ffffff"))
    p.drawText(box, Qt.AlignCenter, label)
    p.restore()


def cursor_at(keys, t):
    """keys: [(time, x, y), ...] with smooth easing between them."""
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            k = smooth((t - t0) / max(1e-6, t1 - t0))
            return lerp(x0, x1, k), lerp(y0, y1, k)
    return keys[-1][1], keys[-1][2]


def draw_cursor(p, x, y, clicks=(), t=0.0):
    for c in clicks:
        lt = t - c
        if 0 <= lt <= 0.5:
            k = lt / 0.5
            p.save()
            p.setOpacity(1 - k)
            p.setPen(QPen(QColor(120, 190, 255), 3))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(x, y), 8 + 26 * k, 8 + 26 * k)
            p.restore()
    p.save()
    p.translate(x, y)
    pts = [(0, 0), (0, 19), (4.6, 14.6), (8.2, 22.5), (11.2, 21.2), (7.7, 13.6), (14, 13.2)]
    p.setPen(QPen(QColor(0, 0, 0), 1.6))
    p.setBrush(QColor("#ffffff"))
    p.drawPolygon(QPolygonF([QPointF(a, b) for a, b in pts]))
    p.restore()


# ------------------------------------------------------------ mock desktops
def wallpaper(p, light):
    g = QLinearGradient(0, 0, W, H)
    if light:
        g.setColorAt(0, QColor("#cfe3ff")); g.setColorAt(1, QColor("#f3e6ff"))
    else:
        g.setColorAt(0, QColor("#0b1330")); g.setColorAt(1, QColor("#2a1245"))
    p.fillRect(0, 0, W, H, g)


def window_frame(p, rect, title, light):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#f4f6fa") if light else QColor("#15181f"))
    p.drawRoundedRect(rect, 8, 8)
    p.setBrush(QColor("#e3e7ee") if light else QColor("#1e222b"))
    p.drawRoundedRect(QRectF(rect.x(), rect.y(), rect.width(), 34), 8, 8)
    p.drawRect(QRectF(rect.x(), rect.y() + 20, rect.width(), 14))
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        p.setBrush(QColor(c))
        p.drawEllipse(QPointF(rect.x() + 20 + i * 22, rect.y() + 17), 6, 6)
    p.setPen(QColor("#4a5568") if light else QColor("#9aa6b8"))
    p.setFont(font(15))
    p.drawText(QRectF(rect.x(), rect.y(), rect.width(), 34), Qt.AlignCenter, title)


def mock_movie(p, t):
    rect = QRectF(40, 40, W - 80, H - 80)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#05060a"))
    p.drawRoundedRect(rect, 8, 8)
    inner = rect.adjusted(0, 0, 0, -52)
    g = QLinearGradient(0, inner.top(), 0, inner.bottom())
    g.setColorAt(0, QColor("#1b1040")); g.setColorAt(0.6, QColor("#7a2f6b")); g.setColorAt(1, QColor("#f08a5d"))
    p.setBrush(g)
    p.drawRoundedRect(inner, 8, 8)
    p.setBrush(QColor(255, 244, 214))
    p.drawEllipse(QPointF(inner.right() - 260, inner.top() + 150), 70, 70)
    p.setBrush(QColor("#0a0612"))
    x = inner.left()
    i = 0
    while x < inner.right():
        hgt = 120 + ((i * 53) % 190)
        p.drawRect(QRectF(x, inner.bottom() - hgt, 62, hgt))
        x += 64
        i += 1
    p.setPen(QColor("#ffffff"))
    p.setFont(font(22))
    p.drawText(QRectF(inner.left(), inner.bottom() - 70, inner.width(), 40), Qt.AlignCenter,
               "“You should be studying.”  “I know.”")
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 60))
    p.drawRoundedRect(QRectF(rect.left() + 30, rect.bottom() - 30, rect.width() - 60, 6), 3, 3)
    p.setBrush(QColor("#e11d48"))
    p.drawRoundedRect(QRectF(rect.left() + 30, rect.bottom() - 30, (rect.width() - 60) * (0.35 + 0.01 * t), 6), 3, 3)


def mock_code(p, light, typed="", caret_line=None, highlight=None, t=0.0):
    rect = QRectF(40, 40, W - 80, H - 80)
    window_frame(p, rect, "solver.py — Editor", light)
    p.setFont(font(19, mono=True))
    colors = (["#0b57d0", "#8a1c8a", "#1a7f37", "#4a5568"] if light else ["#7aa2f7", "#bb9af7", "#9ece6a", "#9aa6b8"])
    lines = ["import numpy as np", "", "def solve(matrix, target):", "    result = np.linalg.solve(matrix, target)",
             "    # TODO: verify the solution", "    return result", "", "A = np.array([[3, 1], [1, 2]])",
             "b = np.array([9, 8])", "answer = solve(A, b)"]
    y0 = rect.y() + 78
    for i, ln in enumerate(lines):
        y = y0 + i * 38
        if highlight == i:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(60, 130, 255, 55))
            p.drawRect(QRectF(rect.x() + 60, y - 24, rect.width() - 80, 34))
        p.setPen(QColor("#9aa6b8") if not light else QColor("#8a94a6"))
        p.drawText(QPointF(rect.x() + 22, y), str(i + 1))
        p.setPen(QColor(colors[(i * 7) % 4] if ln.strip() else colors[3]))
        p.drawText(QPointF(rect.x() + 70, y), ln)
    if caret_line is not None:
        y = y0 + caret_line * 38
        p.setPen(QColor("#e6eefc") if not light else QColor("#14202b"))
        p.drawText(QPointF(rect.x() + 70, y), typed)
        if int(t * 2) % 2 == 0:
            cw = p.fontMetrics().horizontalAdvance(typed)
            p.drawLine(QPointF(rect.x() + 72 + cw, y - 20), QPointF(rect.x() + 72 + cw, y + 6))


def mock_web(p, light=True):
    rect = QRectF(40, 40, W - 80, H - 80)
    window_frame(p, rect, "Qt for Python — Documentation", light)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#ffffff") if light else QColor("#10141b"))
    p.drawRect(QRectF(rect.x(), rect.y() + 34, rect.width(), rect.height() - 34))
    p.setFont(font(34, bold=True))
    p.setPen(QColor("#1b2330") if light else QColor("#e6eefc"))
    p.drawText(QPointF(rect.x() + 60, rect.y() + 110), "Signals & Slots")
    p.setBrush(QColor("#d7dde8") if light else QColor("#2a3342"))
    p.setPen(Qt.NoPen)
    for i in range(14):
        w = rect.width() - 220 - ((i * 97) % 260)
        p.drawRoundedRect(QRectF(rect.x() + 60, rect.y() + 150 + i * 30, w, 12), 6, 6)
    p.setBrush(QColor("#2563eb"))
    p.drawRoundedRect(QRectF(rect.x() + 60, rect.y() + 150 + 14 * 30 + 6, 160, 12), 6, 6)


def desktop(p, kind, light, t=0.0, **kw):
    wallpaper(p, light)
    {"movie": lambda: mock_movie(p, t),
     "code": lambda: mock_code(p, light, t=t, **kw),
     "web": lambda: mock_web(p, light)}[kind]()


# ------------------------------------------------------------------ the demo
class Demo:
    def __init__(self):
        from lucent import theme
        from lucent.config import Look, save_mode, save_overlay_registry
        from lucent.hub import HubWindow
        from lucent.manager import Manager
        from lucent.overlay import OverlayWindow
        self.theme = theme
        os.makedirs(WORK, exist_ok=True)
        self._make_docs()
        save_mode("dark")
        save_overlay_registry([
            {"id": "s1", "name": "Assignment 4", "source": r"C:\Study\assignment4.pdf", "look": {"hue": 170},
             "geometry": [0, 0, 900, 600]},
            {"id": "s2", "name": "Video script", "source": "note:intro", "look": {"hue": 300},
             "geometry": [0, 0, 900, 600]},
            {"id": "s3", "name": "Qt docs", "source": "https://doc.qt.io", "look": {"hue": 215},
             "geometry": [0, 0, 900, 600]},
        ])
        theme.set_mode("dark")
        self.mgr = Manager([])
        QApplication.instance().setPalette(theme.app_palette())

        self.ov = OverlayWindow(Look(hue=215, opacity=0.88), f"{WORK}/notes.pdf", index=1, name="Signals notes")
        self.ov.resize(620, 390)
        self.ov.show()
        self.ov2 = OverlayWindow(Look(hue=215, opacity=0.88), f"{WORK}/readme.md", index=2, name="Docs notes")
        self.ov2.resize(620, 390)
        self.ov2.show()
        self.hub = HubWindow(self.mgr)
        self.hub.resize(440, 500)
        self.hub.show()
        self.hub.refresh([])
        self._settle()
        self._cache = {}
        self.mode = "dark"
        self.invert = False

    @staticmethod
    def _make_docs():
        w = QPdfWriter(f"{WORK}/notes.pdf")
        w.setPageSize(QPageSize(QPageSize.A4))
        w.setResolution(110)
        p = QPainter(w)
        p.setFont(font(40, bold=True))
        p.drawText(80, 160, "Signals & Slots")
        p.setFont(font(24))
        y = 250
        for ln in ["Signals are emitted when something happens.", "Slots are the functions that react.", "",
                   "Key points", "  1. A signal can connect to many slots.", "  2. Slots can be plain callables.",
                   "  3. Across threads, calls are queued.", "", "Example",
                   "  button.clicked.connect(self.on_click)", "  worker.finished.connect(self.on_done)"]:
            p.drawText(80, y, ln)
            y += 52
        p.end()
        with open(f"{WORK}/readme.md", "w") as f:
            f.write("# Quick notes\n\nUse Ctrl+I to flip to a dark, high-contrast\nview when the page behind is bright.\n\n"
                    "- opacity: Ctrl+Up / Ctrl+Down\n- hue: Ctrl+Left / Ctrl+Right\n- ghost mode: Ctrl+Alt+M\n")

    def _settle(self):
        app = QApplication.instance()
        for _ in range(25):
            app.processEvents()

    # -- widget -> pixmap (cached on a state key so we only grab on change)
    def grab(self, widget, key):
        k = (id(widget), key)
        if k not in self._cache:
            self._settle()
            self._cache[k] = widget.grab()
        return self._cache[k]

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        self.theme.set_mode(mode)
        QApplication.instance().setPalette(self.theme.app_palette())
        for w in (self.ov, self.ov2):
            w._retheme()
        self.hub.apply_theme(self.hub._hue)
        self.hub.refresh([])
        self._settle()

    def overlay_frame(self, ov, tag=""):
        return self.grab(ov, (self.mode, self.invert, ov.look.hue, ov.titlebar.isVisible(), tag))

    # ------------------------------------------------------------ scenes
    def render_frame(self, t, out):
        p = QPainter(out)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.TextAntialiasing)
        for start, end, fn in self.SCENES:
            if start <= t < end:
                fn(self, p, t - start, end - start)
                break
        p.end()

    # S0 intro -----------------------------------------------------------
    def s_intro(self, p, t, dur):
        from lucent.icon import draw_moon
        g = QRadialGradient(QPointF(W / 2, H / 2 - 40), 700)
        g.setColorAt(0, QColor("#16224a")); g.setColorAt(1, QColor("#05070f"))
        p.fillRect(0, 0, W, H, g)
        prog = smooth(t / 1.4)
        draw_moon(p, QRectF(W / 2 - 130, 90, 260, 260), progress=prog, glow=0.6 * prog,
                  opacity=smooth(t / 0.5), rotation=-60 * (1 - prog))
        text = "Hey there, I'm Snehil."
        n = int(len(text) * smooth((t - 0.9) / 1.6))
        p.setFont(font(64, bold=True))
        p.setPen(QColor("#e6eefc"))
        p.setOpacity(fade_window(t, dur, 0.1, 0.5))
        p.drawText(QRectF(0, 420, W, 100), Qt.AlignCenter, text[:n])
        p.setOpacity(1)

    # S1-S3 the three people ---------------------------------------------
    def s_problem(self, kind_idx):
        texts = ["You're a workaholic, but you still want to enjoy a movie while reading the docs?",
                 "Or a student buried in assignments, with a series calling your name?",
                 "Or a YouTuber who needs a script on screen that viewers never see?"]

        def fn(self, p, t, dur):
            if kind_idx == 0:
                desktop(p, "movie", False, t)
            elif kind_idx == 1:
                desktop(p, "movie", False, t + 30)
            else:
                desktop(p, "code", False, t)
            if kind_idx == 0:
                # little docs window peeking over the movie
                p.setOpacity(1)
                p.save()
                p.translate(60, 70)
                p.scale(0.55, 0.55)
                mock_web(p, False)
                p.restore()
            caption(p, texts[kind_idx], t, dur)
        return fn

    # S4 splash ------------------------------------------------------------
    def s_splash(self, p, t, dur):
        from lucent.splash import Splash
        wallpaper(p, False)
        p.fillRect(0, 0, W, H, QColor(0, 0, 0, 120))
        if not hasattr(self, "_splash"):
            self._splash = Splash()
            self._splash.show()
        k = clamp(t / (dur - 0.3)) * 0.98
        self._splash._t = k
        self._splash.update()
        pm = self._splash.grab()
        p.drawPixmap(int((W - pm.width()) / 2), int((H - pm.height()) / 2) - 30, pm)
        caption(p, "Lucent solves all of it.", t, dur)

    # S5 hub -> new overlay ---------------------------------------------------
    HUB_X, HUB_Y, OV_X, OV_Y = 420, 40, 330, 96

    def s_hub(self, p, t, dur):
        self.set_mode("dark")
        desktop(p, "movie", False, t + 20)
        path = r"C:\Study\signals-and-slots.pdf"
        typed = path[:int(len(path) * smooth((t - 2.3) / 2.4))]
        self.hub.input_box.setText(typed)
        hub_op = smooth(t / 0.9) * (1 - smooth((t - 5.8) / 0.8))
        ov_op = smooth((t - 5.8) / 0.9) * 0.88
        hx, hy = self.HUB_X, self.HUB_Y
        if hub_op > 0:
            pm = self.grab(self.hub, ("typed", typed))
            p.setOpacity(hub_op)
            p.drawPixmap(hx, hy, pm)
            p.setOpacity(1)
        if ov_op > 0:
            self.ov.titlebar.setVisible(False)
            pm = self.overlay_frame(self.ov)
            p.setOpacity(ov_op)
            p.drawPixmap(self.OV_X, self.OV_Y + int((1 - smooth((t - 5.8) / 0.9)) * 30), pm)
            p.setOpacity(1)
        cur = cursor_at([(0.0, 980, 560), (1.0, 980, 560), (2.2, hx + 170, hy + 108), (4.8, hx + 170, hy + 108),
                         (5.6, hx + 376, hy + 108), (7.0, 1040, 560)], t)
        draw_cursor(p, cur[0], cur[1], clicks=[5.7], t=t)
        caption(p, "Paste a link or a file path in the Hub, press Add, and your overlay appears.", t, dur)

    # S6 opacity over a movie --------------------------------------------------
    def s_opacity(self, p, t, dur):
        desktop(p, "movie", False, t + 28)
        self.ov.titlebar.setVisible(False)
        op = 0.88
        if t > 2.2:
            op = lerp(0.88, 0.42, smooth((t - 2.2) / 1.2))
        if t > 5.2:
            op = lerp(0.42, 0.88, smooth((t - 5.2) / 1.0))
        pm = self.overlay_frame(self.ov)
        p.setOpacity(op)
        p.drawPixmap(self.OV_X, self.OV_Y, pm)
        p.setOpacity(1)
        keycap(p, "Ctrl + ↓", t, 2.0)
        keycap(p, "Ctrl + ↑", t, 5.0)
        caption(p, "Read on top of the movie. Fade the overlay until you can enjoy both.", t, dur)

    # S7 ghost mode --------------------------------------------------------------
    def s_ghost(self, p, t, dur):
        self.set_mode("dark")
        ghost_on = t > 0.9
        self.ov.titlebar.set_click_through(ghost_on)
        self.ov.titlebar.setVisible(t < 2.4)
        typed = "print(answer)"[:max(0, int(13 * smooth((t - 4.4) / 2.0)))]
        clicked = t > 3.8
        desktop(p, "code", False, t, typed=typed if clicked else "", caret_line=10 if clicked else None,
                highlight=10 if clicked else None)
        pm = self.overlay_frame(self.ov, ("ghost", ghost_on))
        p.setOpacity(0.55)
        p.drawPixmap(self.OV_X, self.OV_Y, pm)
        p.setOpacity(1)
        keycap(p, "Ctrl + Alt + M", t, 0.5)
        if ghost_on:
            p.setFont(font(18, bold=True))
            lab = "click-through ON"
            w = p.fontMetrics().horizontalAdvance(lab) + 52
            box = QRectF(self.OV_X, self.OV_Y - 44, w, 34)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(8, 12, 20, 220))
            p.drawRoundedRect(box, 8, 8)
            p.setBrush(QColor("#4ade80"))
            p.drawEllipse(QPointF(box.x() + 20, box.center().y()), 6, 6)
            p.setPen(QColor("#4ade80"))
            p.drawText(box.adjusted(36, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, lab)
        cur = cursor_at([(0, 1100, 600), (2.6, 1100, 600), (3.7, 700, 410), (7.0, 700, 410)], t)
        draw_cursor(p, cur[0], cur[1], clicks=[3.8], t=t)
        caption(p, "Ghost mode: click and type straight through to the app underneath.", t, dur)
        if t > dur - 0.05:
            self.ov.titlebar.set_click_through(False)

    # S8 invert + hue -------------------------------------------------------------
    def s_invert(self, p, t, dur):
        self.set_mode("dark")
        want = t > 2.6
        if want != self.invert:
            self.ov2.toggle_invert_colors()
            self.invert = want
        hue = 215 if t < 5.0 else int(lerp(215, 300, smooth((t - 5.0) / 1.6)))
        if hue != self.ov2.look.hue:
            self.ov2.set_hue(hue)
        self.ov2.titlebar.setVisible(False)
        desktop(p, "web", True, t)
        pm = self.overlay_frame(self.ov2, "inv")
        p.setOpacity(0.9)
        p.drawPixmap(self.OV_X + 40, self.OV_Y, pm)
        p.setOpacity(1)
        keycap(p, "Ctrl + I", t, 2.4)
        keycap(p, "Ctrl + ← →", t, 5.0, dur=2.0)
        caption(p, "Need more contrast? Ctrl+I makes notes dark and crisp, and Ctrl+← → shifts the hue.", t, dur)

    # S9 hidden from recordings ----------------------------------------------------
    def s_capture(self, p, t, dur):
        self.set_mode("dark")
        if self.invert:
            self.ov2.toggle_invert_colors()
            self.invert = False
        pm = self.overlay_frame(self.ov, "plain")
        wallpaper(p, False)
        for i, label in enumerate(("What you see", "What your viewers see")):
            sx, sy, s = 60 + i * 620, 150, 0.46
            p.save()
            p.translate(sx, sy)
            p.scale(s, s)
            desktop(p, "movie", False, t)
            if i == 0:
                self.ov.titlebar.setVisible(False)
                p.setOpacity(0.88)
                p.drawPixmap(self.OV_X + 60, self.OV_Y - 20, pm)
                p.setOpacity(1)
            p.restore()
            p.setPen(QPen(QColor("#e6eefc"), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(sx, sy, W * s, H * s), 8, 8)
            p.setFont(font(26, bold=True))
            p.drawText(QRectF(sx, sy - 56, W * s, 46), Qt.AlignLeft | Qt.AlignVCenter, label)
        p.setBrush(QColor("#ef4444"))
        p.setPen(Qt.NoPen)
        if int(t * 2) % 2 == 0:
            p.drawEllipse(QPointF(60 + 620 + W * 0.46 - 22, 150 + 22), 8, 8)
        p.setFont(font(20))
        p.setPen(QColor("#ef4444"))
        p.drawText(QRectF(60 + 620, 150 + 10, W * 0.46 - 40, 26), Qt.AlignRight | Qt.AlignVCenter, "REC")
        caption(p, "Hidden from screenshots and screen recordings (Windows). Your viewers never see it.", t, dur)

    # S10 light mode -----------------------------------------------------------------
    def s_light(self, p, t, dur):
        flip_at = 2.4
        self.set_mode("light" if t >= flip_at else "dark")
        light = t >= flip_at
        desktop(p, "code" if True else "web", light, t, highlight=None)
        self.ov.titlebar.setVisible(False)
        pm = self.overlay_frame(self.ov, "mode")
        p.setOpacity(0.9)
        p.drawPixmap(self.OV_X + 300, self.OV_Y + 30, pm)
        p.setOpacity(1)
        self.hub.input_box.clear()
        self.hub.refresh([])
        hpm = self.grab(self.hub, ("mode-hub", self.mode))
        p.drawPixmap(60, 60, hpm)
        flash = 1 - smooth((t - flip_at) / 0.5) if t >= flip_at else 0.0
        if flash > 0:
            p.fillRect(0, 0, W, H, QColor(255, 255, 255, int(150 * flash)))
        cur = cursor_at([(0, 700, 620), (1.0, 700, 620), (2.2, 60 + 326, 60 + 18), (3.2, 60 + 326, 60 + 18), (4.4, 900, 600)], t)
        draw_cursor(p, cur[0], cur[1], clicks=[flip_at], t=t)
        keycap(p, "Ctrl + Shift + L", t, 3.4, dur=2.4, y=H - 205, cx=910)
        caption(p, "Dark or light: one click, or Ctrl+Shift+L.", t, dur)

    # S11 end card ---------------------------------------------------------------------
    def s_end(self, p, t, dur):
        from lucent.icon import draw_moon
        g = QRadialGradient(QPointF(W / 2, H / 2 - 60), 760)
        g.setColorAt(0, QColor("#16224a")); g.setColorAt(1, QColor("#05070f"))
        p.fillRect(0, 0, W, H, g)
        a = fade_window(t, dur, 0.6, 0.6)
        p.setOpacity(a)
        draw_moon(p, QRectF(W / 2 - 100, 90, 200, 200), glow=0.6)
        p.setFont(font(72, bold=True))
        p.setPen(QColor("#e6eefc"))
        p.drawText(QRectF(0, 310, W, 100), Qt.AlignCenter, "Lucent")
        p.setFont(font(28))
        p.setPen(QColor(230, 238, 252, 210))
        p.drawText(QRectF(0, 420, W, 44), Qt.AlignCenter, "A transparent, always-on-top viewer for Windows and Linux")
        p.setFont(font(26, bold=True))
        p.setPen(QColor("#7aa2f7"))
        p.drawText(QRectF(0, 490, W, 44), Qt.AlignCenter, "github.com/snehil-pandey/Lucent")
        p.setOpacity(1)

    SCENES = []


def build_scenes():
    d = Demo
    s = []
    t = 0.0
    for dur, fn in [(4.8, d.s_intro), (5.0, d.s_problem(None, 0)), (4.6, d.s_problem(None, 1)),
                    (4.8, d.s_problem(None, 2)), (3.6, d.s_splash), (8.2, d.s_hub), (8.0, d.s_opacity),
                    (7.4, d.s_ghost), (7.6, d.s_invert), (7.2, d.s_capture), (6.8, d.s_light), (4.6, d.s_end)]:
        s.append((t, t + dur, fn))
        t += dur
    return s, t


def main():
    args = sys.argv[1:]
    app = QApplication([])
    app.setStyle("Fusion")
    demo = Demo()
    Demo.SCENES, total = build_scenes()
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)

    if args and args[0] == "--preview":
        for sec in [float(x) for x in args[1].split(",")]:
            img.fill(QColor("#000000"))
            demo.render_frame(sec, img)
            img.save(f"{WORK}/frame_{sec:05.1f}.png")
            print("wrote", f"{WORK}/frame_{sec:05.1f}.png")
        return 0

    out = args[0] if args else "lucent_demo.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(total * FPS)
    for i in range(n):
        img.fill(QColor("#000000"))
        demo.render_frame(i / FPS, img)
        ff.stdin.write(img.convertToFormat(QImage.Format_RGBA8888).constBits().tobytes())
        if i % (FPS * 5) == 0:
            print(f"  {i / FPS:5.1f}s / {total:.1f}s", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
