"""
VESPER custom HUD widgets — painted controls with sci-fi aesthetic.

HudSlider: Custom-painted slider with thin glowing track, diamond handle,
           integrated label and value readout.
"""

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QFontMetrics,
    QLinearGradient, QPainterPath, QBrush,
)

from vesper.styles import (
    BG_DARKEST, BG_DARK, BG_PANEL, BG_CARD,
    GRID_DIM, GRID_MID, CYAN, CYAN_DIM, CYAN_BRIGHT,
    AMBER, AMBER_DIM, TEXT_PRIMARY, TEXT_DIM, TEXT_BRIGHT, WHITE,
)


def _color(hex_str, alpha=255):
    """Create QColor from hex with optional alpha."""
    c = QColor(hex_str)
    c.setAlpha(alpha)
    return c


class HudSlider(QWidget):
    """
    Custom-painted HUD slider with:
    - Thin glowing track line
    - Diamond-shaped handle with glow halo
    - Integrated parameter label (top-left) and value readout (top-right)
    - Tick marks along the track
    - Accent colour configurable
    """

    valueChanged = Signal(float)

    def __init__(self, label="PARAM", min_val=0.0, max_val=100.0,
                 value=50.0, step=1.0, decimals=0, suffix="",
                 accent=CYAN, parent=None):
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
        self._track_y = 38       # y position of track centre
        self._track_margin = 14  # left/right margin
        self._handle_size = 8    # half-size of diamond

        self.setMinimumHeight(52)
        self.setMaximumHeight(56)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    # ── Properties ──────────────────────────────────────────────────────

    def value(self):
        return self._value

    def setValue(self, v):
        v = max(self._min, min(self._max, v))
        # Snap to step
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

    # ── Geometry helpers ────────────────────────────────────────────────

    def _track_rect(self):
        """Returns (x_start, x_end, y) of the track line."""
        m = self._track_margin
        return m, self.width() - m, self._track_y

    def _val_to_x(self, val):
        x0, x1, _ = self._track_rect()
        if self._max == self._min:
            return x0
        frac = (val - self._min) / (self._max - self._min)
        return x0 + frac * (x1 - x0)

    def _x_to_val(self, x):
        x0, x1, _ = self._track_rect()
        frac = (x - x0) / max(1, x1 - x0)
        frac = max(0.0, min(1.0, frac))
        return self._min + frac * (self._max - self._min)

    # ── Painting ────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        accent = QColor(self._accent)
        accent_dim = QColor(self._accent)
        accent_dim.setAlpha(60)
        accent_glow = QColor(self._accent)
        accent_glow.setAlpha(25)

        x0, x1, ty = self._track_rect()
        hx = self._val_to_x(self._value)
        hs = self._handle_size

        # ── Label (top-left) ──
        label_font = QFont("Consolas", 9)
        label_font.setBold(True)
        label_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        p.setFont(label_font)
        p.setPen(_color(TEXT_DIM))
        p.drawText(x0, 4, 200, 16, Qt.AlignLeft | Qt.AlignVCenter, self._label)

        # ── Value readout (top-right) ──
        val_font = QFont("Consolas", 11)
        val_font.setBold(True)
        p.setFont(val_font)
        p.setPen(accent)
        if self._decimals == 0:
            val_text = f"{int(self._value)}{self._suffix}"
        else:
            val_text = f"{self._value:.{self._decimals}f}{self._suffix}"
        p.drawText(x0, 4, x1 - x0, 16, Qt.AlignRight | Qt.AlignVCenter, val_text)

        # ── Track background (full width, dim) ──
        p.setPen(QPen(_color(GRID_DIM, 100), 1))
        p.drawLine(QPointF(x0, ty), QPointF(x1, ty))

        # ── Track filled portion (left of handle, accent) ──
        grad = QLinearGradient(x0, ty, hx, ty)
        grad.setColorAt(0.0, accent_dim)
        grad.setColorAt(1.0, accent)
        p.setPen(QPen(QBrush(grad), 2))
        p.drawLine(QPointF(x0, ty), QPointF(hx, ty))

        # ── Track glow under filled portion ──
        p.setPen(QPen(accent_glow, 6))
        p.drawLine(QPointF(x0, ty), QPointF(hx, ty))

        # ── Tick marks ──
        n_ticks = 10
        p.setPen(QPen(_color(GRID_DIM, 80), 1))
        for i in range(n_ticks + 1):
            tx = x0 + (x1 - x0) * i / n_ticks
            p.drawLine(QPointF(tx, ty + 4), QPointF(tx, ty + 8))

        # Min/max labels
        tick_font = QFont("Consolas", 7)
        p.setFont(tick_font)
        p.setPen(_color(TEXT_DIM, 100))
        if self._decimals == 0:
            min_t = f"{int(self._min)}"
            max_t = f"{int(self._max)}"
        else:
            min_t = f"{self._min:.{self._decimals}f}"
            max_t = f"{self._max:.{self._decimals}f}"
        p.drawText(QRectF(x0 - 10, ty + 9, 50, 12), Qt.AlignLeft, min_t)
        p.drawText(QRectF(x1 - 40, ty + 9, 50, 12), Qt.AlignRight, max_t)

        # ── Handle: diamond shape ──
        diamond = QPainterPath()
        diamond.moveTo(hx, ty - hs)       # top
        diamond.lineTo(hx + hs, ty)       # right
        diamond.lineTo(hx, ty + hs)       # bottom
        diamond.lineTo(hx - hs, ty)       # left
        diamond.closeSubpath()

        # Outer glow
        glow_size = hs + (5 if self._dragging else 3)
        glow_path = QPainterPath()
        glow_path.moveTo(hx, ty - glow_size)
        glow_path.lineTo(hx + glow_size, ty)
        glow_path.lineTo(hx, ty + glow_size)
        glow_path.lineTo(hx - glow_size, ty)
        glow_path.closeSubpath()
        p.setPen(Qt.NoPen)
        glow_col = QColor(self._accent)
        glow_col.setAlpha(30 if not self._dragging else 50)
        p.setBrush(glow_col)
        p.drawPath(glow_path)

        # Diamond fill
        p.setBrush(accent if self._dragging or self._hover else accent_dim)
        p.setPen(QPen(_color(WHITE, 180), 0.8))
        p.drawPath(diamond)

        # Centre bright point
        p.setPen(Qt.NoPen)
        p.setBrush(_color(WHITE, 200 if self._dragging else 140))
        p.drawEllipse(QPointF(hx, ty), 2, 2)

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
            # Check hover over handle area
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
        """Double-click to type a value directly."""
        from PySide6.QtWidgets import QInputDialog
        if self._decimals == 0:
            val, ok = QInputDialog.getInt(
                self, self._label, f"Enter {self._label}:",
                int(self._value), int(self._min), int(self._max), int(self._step))
        else:
            val, ok = QInputDialog.getDouble(
                self, self._label, f"Enter {self._label}:",
                self._value, self._min, self._max, self._decimals)
        if ok:
            self.setValue(val)

    def _update_from_mouse(self, mouse_x):
        raw = self._x_to_val(mouse_x)
        self.setValue(raw)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
