"""
VESPER custom widgets — Evangelion / NERV instrument panel aesthetic.

Widgets:
  HudSlider     — segmented-bar slider with triangular indicator
  HudTitleBar   — frameless window title bar with drag + controls
  ScenarioTable — comparison table for saved scenarios
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSizePolicy, QApplication,
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSize
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QLinearGradient,
    QPainterPath, QBrush, QPolygonF,
)

from vesper.styles import (
    BG_DARKEST, BG_DARK, BG_PANEL, BG_CARD, BG_TITLEBAR,
    GRID_DIM, GRID_MID, GRID_BRIGHT,
    CYAN, CYAN_DIM, CYAN_BRIGHT,
    AMBER, AMBER_DIM, AMBER_BRIGHT, AMBER_FAINT, AMBER_MUTED,
    RED, RED_DIM,
    TEXT_PRIMARY, TEXT_DIM, TEXT_BRIGHT, TEXT_LABEL, WHITE,
)


def _qc(hex_str, alpha=255):
    c = QColor(hex_str)
    c.setAlpha(alpha)
    return c


# ═══════════════════════════════════════════════════════════════════════════
#  HudSlider — Evangelion segmented bar slider
# ═══════════════════════════════════════════════════════════════════════════

class HudSlider(QWidget):
    """
    Evangelion-style parameter slider:
      - Segmented rectangular bar (filled segments = accent, unfilled = dim)
      - Small downward-pointing triangle indicator above track
      - Label on left, value readout in thin-bordered box on right
      - Sharp edges, no rounded corners, flat military aesthetic
      - Tick marks below track
    """

    valueChanged = Signal(float)

    N_SEGMENTS = 40          # number of bar segments
    SEGMENT_GAP = 1          # px gap between segments

    def __init__(self, label="PARAM", min_val=0.0, max_val=100.0,
                 value=50.0, step=1.0, decimals=0, suffix="",
                 accent=AMBER, parent=None):
        super().__init__(parent)
        self._label = label
        self._min = min_val
        self._max = max_val
        self._value = value
        self._step = step
        self._decimals = decimals
        self._suffix = suffix
        self._accent = accent

        self._dragging = False
        self._hover = False

        # Layout metrics
        self._margin = 10
        self._label_h = 16
        self._indicator_h = 8
        self._bar_y = 30       # top of bar
        self._bar_h = 6        # bar height
        self._tick_h = 4

        total_h = self._bar_y + self._bar_h + self._tick_h + 14
        self.setMinimumHeight(total_h)
        self.setMaximumHeight(total_h + 4)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    # ── Properties ──────────────────────────────────────────────────────

    def value(self):
        return self._value

    def setValue(self, v):
        v = max(self._min, min(self._max, v))
        v = round(v / self._step) * self._step
        v = round(v, self._decimals)
        if v != self._value:
            self._value = v
            self.valueChanged.emit(v)
            self.update()

    def setRange(self, min_val, max_val):
        self._min = min_val
        self._max = max_val
        self.setValue(self._value)

    # ── Geometry ────────────────────────────────────────────────────────

    def _bar_rect(self):
        """(x0, x1, y_top, height) of the segmented bar."""
        return (self._margin, self.width() - self._margin,
                self._bar_y, self._bar_h)

    def _val_to_x(self, val):
        x0, x1, _, _ = self._bar_rect()
        if self._max == self._min:
            return x0
        frac = (val - self._min) / (self._max - self._min)
        return x0 + frac * (x1 - x0)

    def _x_to_val(self, x):
        x0, x1, _, _ = self._bar_rect()
        frac = (x - x0) / max(1, x1 - x0)
        frac = max(0.0, min(1.0, frac))
        return self._min + frac * (self._max - self._min)

    def _frac(self):
        if self._max == self._min:
            return 0.0
        return (self._value - self._min) / (self._max - self._min)

    # ── Painting ────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)  # sharp pixel edges

        accent = QColor(self._accent)
        accent_dim = _qc(self._accent, 30)
        accent_bright = QColor(self._accent)
        accent_bright.setAlpha(220)

        x0, x1, by, bh = self._bar_rect()
        bar_w = x1 - x0
        frac = self._frac()
        hx = self._val_to_x(self._value)

        # ── Label (top-left) ──
        lf = QFont("Consolas", 8)
        lf.setBold(True)
        lf.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        p.setFont(lf)
        p.setPen(_qc(TEXT_LABEL))
        p.drawText(x0, 2, 200, self._label_h,
                   Qt.AlignLeft | Qt.AlignVCenter, self._label)

        # ── Value readout box (top-right) ──
        vf = QFont("Consolas", 10)
        vf.setBold(True)
        p.setFont(vf)

        if self._decimals == 0:
            val_text = f"{int(self._value)}{self._suffix}"
        else:
            val_text = f"{self._value:.{self._decimals}f}{self._suffix}"

        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(val_text) + 12
        th = fm.height() + 4
        vx = x1 - tw
        vy = 1

        # Readout border box
        p.setPen(QPen(_qc(GRID_MID), 1))
        p.setBrush(_qc(BG_DARKEST, 200))
        p.drawRect(QRectF(vx, vy, tw, th))

        # Readout text
        p.setPen(accent_bright if self._dragging else accent)
        p.drawText(QRectF(vx, vy, tw, th),
                   Qt.AlignCenter, val_text)

        # ── Triangular indicator above bar ──
        tri_size = 5
        tri_y = by - 2
        tri = QPolygonF([
            QPointF(hx - tri_size, tri_y - tri_size - 1),
            QPointF(hx + tri_size, tri_y - tri_size - 1),
            QPointF(hx, tri_y),
        ])
        p.setPen(Qt.NoPen)
        p.setBrush(accent if self._dragging else _qc(self._accent, 180))
        p.drawPolygon(tri)

        # ── Segmented bar ──
        seg_total_w = bar_w
        gap = self.SEGMENT_GAP
        n = self.N_SEGMENTS
        seg_w = (seg_total_w - gap * (n - 1)) / n

        filled_segments = int(frac * n)
        partial_frac = (frac * n) - filled_segments

        for i in range(n):
            sx = x0 + i * (seg_w + gap)

            if i < filled_segments:
                # Fully filled segment
                p.setPen(Qt.NoPen)
                p.setBrush(accent)
                p.drawRect(QRectF(sx, by, seg_w, bh))
            elif i == filled_segments and partial_frac > 0.15:
                # Partially filled
                p.setPen(Qt.NoPen)
                p.setBrush(_qc(self._accent, 120))
                p.drawRect(QRectF(sx, by, seg_w, bh))
            else:
                # Unfilled segment
                p.setPen(Qt.NoPen)
                p.setBrush(_qc(GRID_DIM, 80))
                p.drawRect(QRectF(sx, by, seg_w, bh))

        # ── Bar border ──
        p.setPen(QPen(_qc(GRID_MID, 100), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(x0 - 1, by - 1, bar_w + 2, bh + 2))

        # ── Subtle glow under filled portion ──
        if frac > 0:
            p.setRenderHint(QPainter.Antialiasing, True)
            glow_pen = QPen(_qc(self._accent, 15), bh + 6)
            p.setPen(glow_pen)
            glow_end = x0 + frac * bar_w
            p.drawLine(QPointF(x0, by + bh / 2),
                       QPointF(glow_end, by + bh / 2))
            p.setRenderHint(QPainter.Antialiasing, False)

        # ── Tick marks below bar ──
        n_ticks = 10
        tick_y = by + bh + 2
        p.setPen(QPen(_qc(GRID_DIM, 100), 1))
        for i in range(n_ticks + 1):
            tx = x0 + bar_w * i / n_ticks
            h = self._tick_h if i % 5 == 0 else self._tick_h - 1
            p.drawLine(QPointF(tx, tick_y), QPointF(tx, tick_y + h))

        # ── Min/max labels ──
        tf = QFont("Consolas", 7)
        p.setFont(tf)
        p.setPen(_qc(TEXT_DIM, 120))
        label_y = tick_y + self._tick_h + 1
        if self._decimals == 0:
            min_t, max_t = f"{int(self._min)}", f"{int(self._max)}"
        else:
            min_t = f"{self._min:.{self._decimals}f}"
            max_t = f"{self._max:.{self._decimals}f}"
        p.drawText(QRectF(x0 - 5, label_y, 60, 10), Qt.AlignLeft, min_t)
        p.drawText(QRectF(x1 - 55, label_y, 60, 10), Qt.AlignRight, max_t)

        p.end()

    # ── Mouse handling ──────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._update_from_mouse(event.position().x())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_from_mouse(event.position().x())
        else:
            hx = self._val_to_x(self._value)
            self._hover = abs(event.position().x() - hx) < 15
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.setValue(self._value + self._step)
        elif delta < 0:
            self.setValue(self._value - self._step)

    def mouseDoubleClickEvent(self, event):
        from PySide6.QtWidgets import QInputDialog
        if self._decimals == 0:
            val, ok = QInputDialog.getInt(
                self, self._label, f"Enter {self._label}:",
                int(self._value), int(self._min), int(self._max),
                int(self._step))
        else:
            val, ok = QInputDialog.getDouble(
                self, self._label, f"Enter {self._label}:",
                self._value, self._min, self._max, self._decimals)
        if ok:
            self.setValue(val)

    def _update_from_mouse(self, mx):
        self.setValue(self._x_to_val(mx))

    def leaveEvent(self, event):
        self._hover = False
        self.update()


# ═══════════════════════════════════════════════════════════════════════════
#  HudTitleBar — Custom frameless window title bar
# ═══════════════════════════════════════════════════════════════════════════

class HudTitleBar(QWidget):
    """
    Evangelion-style custom title bar:
      - Thin amber accent lines top and bottom
      - Title text and subtitle
      - Angular min / max / close buttons
      - Supports drag-to-move and double-click maximize
    """

    def __init__(self, window, title="VESPER", subtitle="", parent=None):
        super().__init__(parent)
        self._window = window
        self._title = title
        self._subtitle = subtitle
        self._drag_pos = None
        self._maximized = False

        self.setFixedHeight(32)
        self.setMouseTracking(True)
        self.setCursor(Qt.ArrowCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()

        # Background
        p.fillRect(0, 0, w, h, QColor(BG_TITLEBAR))

        # Top accent line
        p.setPen(QPen(QColor(AMBER), 1))
        p.drawLine(0, 0, w, 0)

        # Bottom border
        p.setPen(QPen(_qc(GRID_DIM), 1))
        p.drawLine(0, h - 1, w, h - 1)

        # Left decorative bracket
        p.setPen(QPen(_qc(AMBER_DIM), 1))
        p.drawLine(8, 8, 8, h - 8)
        p.drawLine(8, 8, 14, 8)
        p.drawLine(8, h - 8, 14, h - 8)

        # Title
        tf = QFont("Consolas", 10)
        tf.setBold(True)
        tf.setLetterSpacing(QFont.AbsoluteSpacing, 4.0)
        p.setFont(tf)
        p.setPen(QColor(AMBER))
        p.drawText(22, 0, w - 140, h, Qt.AlignLeft | Qt.AlignVCenter,
                   self._title)

        # Subtitle
        if self._subtitle:
            sf = QFont("Consolas", 7)
            sf.setLetterSpacing(QFont.AbsoluteSpacing, 2.0)
            p.setFont(sf)
            p.setPen(_qc(TEXT_DIM))
            fm = p.fontMetrics()
            title_w = QFont("Consolas", 10)
            title_w.setBold(True)
            title_w.setLetterSpacing(QFont.AbsoluteSpacing, 4.0)
            title_fm_w = p.fontMetrics()
            p.setFont(QFont("Consolas", 10))
            tw = p.fontMetrics().horizontalAdvance(self._title) + 40
            p.setFont(sf)
            p.drawText(22 + tw, 0, w - 140 - tw, h,
                       Qt.AlignLeft | Qt.AlignVCenter, self._subtitle)

        # Right decorative bracket
        p.setPen(QPen(_qc(AMBER_DIM), 1))
        rx = w - 110
        p.drawLine(rx, 8, rx, h - 8)
        p.drawLine(rx - 6, 8, rx, 8)
        p.drawLine(rx - 6, h - 8, rx, h - 8)

        # ── Window control buttons ──
        btn_w, btn_h = 24, 16
        btn_y = (h - btn_h) // 2

        # Minimize  ─
        bx = w - 88
        p.setPen(QPen(_qc(TEXT_DIM), 1))
        p.drawRect(QRectF(bx, btn_y, btn_w, btn_h))
        p.setPen(QPen(_qc(TEXT_PRIMARY), 1))
        p.drawLine(bx + 7, btn_y + btn_h // 2,
                   bx + btn_w - 7, btn_y + btn_h // 2)

        # Maximize  □
        bx = w - 60
        p.setPen(QPen(_qc(TEXT_DIM), 1))
        p.drawRect(QRectF(bx, btn_y, btn_w, btn_h))
        p.setPen(QPen(_qc(TEXT_PRIMARY), 1))
        p.drawRect(QRectF(bx + 6, btn_y + 3, btn_w - 12, btn_h - 6))

        # Close  ×
        bx = w - 32
        p.setPen(QPen(_qc(RED_DIM), 1))
        p.drawRect(QRectF(bx, btn_y, btn_w, btn_h))
        p.setPen(QPen(_qc(RED), 1))
        p.drawLine(bx + 7, btn_y + 4, bx + btn_w - 7, btn_y + btn_h - 4)
        p.drawLine(bx + 7, btn_y + btn_h - 4, bx + btn_w - 7, btn_y + 4)

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Check button regions
            x = event.position().x()
            w = self.width()
            btn_y_top = 4
            btn_y_bot = 28

            if w - 88 <= x <= w - 64:
                self._window.showMinimized()
                return
            elif w - 60 <= x <= w - 36:
                self._toggle_maximize()
                return
            elif w - 32 <= x <= w - 8:
                self._window.close()
                return

            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            if self._maximized:
                # Un-maximize when dragging
                self._toggle_maximize()
            delta = event.globalPosition().toPoint() - self._drag_pos
            self._window.move(self._window.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self._toggle_maximize()

    def _toggle_maximize(self):
        if self._maximized:
            self._window.showNormal()
            self._maximized = False
        else:
            self._window.showMaximized()
            self._maximized = True


# ═══════════════════════════════════════════════════════════════════════════
#  ScenarioTable — painted comparison table
# ═══════════════════════════════════════════════════════════════════════════

class ScenarioTable(QWidget):
    """
    Custom-painted comparison table for saved scenarios.
    Shows scenarios as rows with columns for key metrics.
    """

    removeRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scenarios = []
        self._hover_row = -1
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    ROW_H = 24
    HEADER_H = 22
    COL_WIDTHS = [130, 80, 70, 60, 50]  # name, dv, time, method, burns
    COL_HEADERS = ["SCENARIO", "\u0394v m/s", "TIME", "METHOD", "BURNS"]

    def set_scenarios(self, scenarios):
        self._scenarios = scenarios
        self.setMinimumHeight(
            self.HEADER_H + max(1, len(scenarios)) * self.ROW_H + 4
        )
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w = self.width()

        # Calculate proportional column widths
        total_fixed = sum(self.COL_WIDTHS)
        scale = (w - 20) / total_fixed if total_fixed > 0 else 1.0
        cols = [int(cw * scale) for cw in self.COL_WIDTHS]

        # ── Header ──
        hf = QFont("Consolas", 7)
        hf.setBold(True)
        hf.setLetterSpacing(QFont.AbsoluteSpacing, 1.0)
        p.setFont(hf)
        p.setPen(_qc(AMBER_DIM))

        x = 4
        for i, hdr in enumerate(self.COL_HEADERS):
            p.drawText(QRectF(x, 2, cols[i], self.HEADER_H),
                       Qt.AlignLeft | Qt.AlignVCenter, hdr)
            x += cols[i]

        # Header underline
        p.setPen(QPen(_qc(GRID_DIM), 1))
        p.drawLine(4, self.HEADER_H, w - 4, self.HEADER_H)

        if not self._scenarios:
            p.setPen(_qc(TEXT_DIM, 100))
            nf = QFont("Consolas", 9)
            p.setFont(nf)
            p.drawText(QRectF(4, self.HEADER_H, w - 8, 40),
                       Qt.AlignCenter, "No saved scenarios")
            p.end()
            return

        # ── Data rows ──
        rf = QFont("Consolas", 8)
        p.setFont(rf)

        # Find best dv for highlighting
        best_dv = min(s.best_dv for s in self._scenarios) if self._scenarios else 0

        for row, sc in enumerate(self._scenarios):
            ry = self.HEADER_H + row * self.ROW_H

            # Hover highlight
            if row == self._hover_row:
                p.fillRect(QRectF(2, ry, w - 4, self.ROW_H),
                           _qc(AMBER_FAINT, 40))

            # Alternating row tint
            if row % 2 == 0:
                p.fillRect(QRectF(2, ry, w - 4, self.ROW_H),
                           _qc(BG_PANEL, 60))

            x = 4
            # Name
            p.setPen(_qc(TEXT_PRIMARY))
            p.drawText(QRectF(x, ry, cols[0], self.ROW_H),
                       Qt.AlignLeft | Qt.AlignVCenter, sc.name)
            x += cols[0]

            # Delta-v (highlight best)
            is_best = abs(sc.best_dv - best_dv) < 0.1
            p.setPen(QColor(AMBER_BRIGHT) if is_best else _qc(TEXT_PRIMARY))
            p.drawText(QRectF(x, ry, cols[1], self.ROW_H),
                       Qt.AlignLeft | Qt.AlignVCenter,
                       f"{sc.best_dv:.0f}")
            x += cols[1]

            # Time
            p.setPen(_qc(TEXT_DIM))
            time_str = _fmt_time(sc.best_time)
            p.drawText(QRectF(x, ry, cols[2], self.ROW_H),
                       Qt.AlignLeft | Qt.AlignVCenter, time_str)
            x += cols[2]

            # Method
            p.setPen(_qc(TEXT_DIM))
            method_short = sc.best_method[:12]
            p.drawText(QRectF(x, ry, cols[3], self.ROW_H),
                       Qt.AlignLeft | Qt.AlignVCenter, method_short)
            x += cols[3]

            # Burns
            p.setPen(_qc(TEXT_DIM))
            p.drawText(QRectF(x, ry, cols[4], self.ROW_H),
                       Qt.AlignLeft | Qt.AlignVCenter, str(sc.n_burns))

            # Row bottom line
            p.setPen(QPen(_qc(GRID_DIM, 60), 1))
            p.drawLine(4, ry + self.ROW_H - 1, w - 4, ry + self.ROW_H - 1)

        p.end()

    def mouseMoveEvent(self, event):
        y = event.position().y()
        row = int((y - self.HEADER_H) / self.ROW_H)
        if 0 <= row < len(self._scenarios):
            if row != self._hover_row:
                self._hover_row = row
                self.update()
        else:
            if self._hover_row != -1:
                self._hover_row = -1
                self.update()

    def mouseDoubleClickEvent(self, event):
        y = event.position().y()
        row = int((y - self.HEADER_H) / self.ROW_H)
        if 0 <= row < len(self._scenarios):
            self.removeRequested.emit(row)

    def leaveEvent(self, event):
        self._hover_row = -1
        self.update()


def _fmt_time(seconds):
    h = seconds / 3600.0
    if h < 1:
        return f"{seconds / 60:.0f}m"
    elif h < 48:
        return f"{h:.1f}h"
    return f"{h / 24:.1f}d"
