"""
VESPER colour palette and Qt stylesheet definitions.
Central place for all visual theming constants.
"""

# ── Colour Palette ──────────────────────────────────────────────────────────

BG_DARKEST = "#000000"
BG_DARK = "#010108"
BG_PANEL = "#06060e"
BG_CARD = "#0a0a16"
BG_INPUT = "#080812"

GRID_DIM = "#12182a"
GRID_MID = "#1c2640"

CYAN = "#00e5ff"
CYAN_DIM = "#005f6e"
CYAN_GLOW = "#00e5ff"
CYAN_BRIGHT = "#60f8ff"

AMBER = "#ffab00"
AMBER_DIM = "#7a5200"
AMBER_BRIGHT = "#ffd060"

RED = "#ff1744"
RED_DIM = "#6e0a1e"

GREEN = "#00e676"

TEXT_PRIMARY = "#b8c8dc"
TEXT_DIM = "#506078"
TEXT_BRIGHT = "#e0ecf8"

WHITE = "#f0f4f8"

# ── Matplotlib colours (for plots) ──────────────────────────────────────────

MPL_BG = BG_DARKEST
MPL_FACE = BG_DARK
MPL_GRID = "#0e1420"
MPL_TEXT = TEXT_PRIMARY

ORBIT_INITIAL = CYAN
ORBIT_INITIAL_GLOW = "#00e5ff"
ORBIT_TARGET = AMBER
ORBIT_TARGET_GLOW = "#ffab00"
ORBIT_TRANSFER = "#b388ff"  # soft violet for transfer arcs
ORBIT_TRANSFER_GLOW = "#9060ee"
ORBIT_TRANSFER_2 = "#ff80ab"  # pink for bi-elliptic second arc
BURN_MARKER = RED
EARTH_WIRE = "#1a6fa8"       # wireframe line colour
EARTH_WIRE_GLOW = "#0d3a5c"  # dim glow behind wireframe
EARTH_FILL = "#020810"       # nearly invisible fill

# ── Qt Stylesheet ───────────────────────────────────────────────────────────

QSS = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: "Consolas", "SF Mono", "Fira Code", "Source Code Pro", monospace;
    font-size: 12px;
}}

QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
    padding: 1px;
}}

QLabel[class="heading"] {{
    color: {CYAN};
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 4px 0px;
}}

QLabel[class="value"] {{
    color: {TEXT_BRIGHT};
    font-size: 18px;
    font-weight: bold;
}}

QLabel[class="unit"] {{
    color: {TEXT_DIM};
    font-size: 11px;
}}

QLabel[class="best"] {{
    color: {GREEN};
    font-size: 12px;
    font-weight: bold;
}}

QLabel[class="section"] {{
    color: {CYAN};
    font-size: 11px;
    font-weight: bold;
    border-bottom: 1px solid {GRID_DIM};
    padding-bottom: 3px;
    margin-top: 6px;
}}

QGroupBox {{
    border: 1px solid {GRID_DIM};
    border-radius: 3px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    background-color: {BG_PANEL};
    font-size: 11px;
    color: {TEXT_DIM};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {CYAN};
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 1px;
}}

QSlider::groove:horizontal {{
    border: 1px solid {GRID_DIM};
    height: 4px;
    background: {BG_CARD};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {CYAN};
    border: 1px solid {CYAN_DIM};
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}

QSlider::sub-page:horizontal {{
    background: {CYAN_DIM};
    border-radius: 2px;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {BG_INPUT};
    border: 1px solid {GRID_DIM};
    border-radius: 2px;
    color: {TEXT_BRIGHT};
    padding: 3px 6px;
    font-size: 12px;
    selection-background-color: {CYAN_DIM};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: {BG_CARD};
    border: 1px solid {GRID_DIM};
    width: 16px;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {TEXT_DIM};
    width: 0; height: 0;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_DIM};
    width: 0; height: 0;
}}

QPushButton {{
    background-color: {BG_CARD};
    border: 1px solid {GRID_DIM};
    border-radius: 2px;
    color: {CYAN};
    padding: 6px 14px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}

QPushButton:hover {{
    border-color: {CYAN_DIM};
    background-color: {BG_PANEL};
}}

QPushButton:pressed {{
    background-color: {CYAN_DIM};
    color: {BG_DARKEST};
}}

QPushButton[class="preset"] {{
    padding: 4px 10px;
    font-size: 10px;
}}

QFrame[class="separator"] {{
    background-color: {GRID_DIM};
    max-height: 1px;
    min-height: 1px;
}}

QSplitter::handle {{
    background-color: {GRID_DIM};
    width: 1px;
    height: 1px;
}}

QStatusBar {{
    background-color: {BG_DARKEST};
    color: {TEXT_DIM};
    border-top: 1px solid {GRID_DIM};
    font-size: 10px;
}}
"""
