"""
VESPER colour palette and Qt stylesheet — Evangelion / NERV aesthetic.

Design language:
  - Hard edges, no rounded corners, angular geometry
  - Amber/orange primary, cyan secondary, red for warnings
  - Thin bright border lines on near-black backgrounds
  - Monospace all-caps labels with letter spacing
  - Flat, military-industrial instrument panel feel
  - Subtle segmented indicators, not soft glowing halos
"""

# ── Colour Palette ──────────────────────────────────────────────────────────

# Backgrounds — near-black with faint blue-purple tint
BG_DARKEST = "#000000"
BG_DARK = "#020208"
BG_PANEL = "#06060e"
BG_CARD = "#0a0a14"
BG_INPUT = "#080810"
BG_TITLEBAR = "#030306"

# Grid / structural lines
GRID_DIM = "#141828"
GRID_MID = "#1e2844"
GRID_BRIGHT = "#283460"

# Primary accent — Evangelion orange/amber
AMBER = "#ff8c00"
AMBER_DIM = "#663800"
AMBER_GLOW = "#ff9500"
AMBER_BRIGHT = "#ffb840"
AMBER_MUTED = "#8a4e00"
AMBER_FAINT = "#331c00"

# Secondary — NERV teal/cyan
CYAN = "#00c8e0"
CYAN_DIM = "#004858"
CYAN_GLOW = "#00d4f0"
CYAN_BRIGHT = "#50e8ff"
CYAN_MUTED = "#007888"
CYAN_FAINT = "#001820"

# Alert / warning
RED = "#ff1744"
RED_DIM = "#5a0a18"
RED_GLOW = "#ff3060"

# Status / success
GREEN = "#00e676"
GREEN_DIM = "#004d28"

# Text hierarchy
TEXT_PRIMARY = "#c0c8d8"
TEXT_DIM = "#4a5878"
TEXT_BRIGHT = "#e8f0ff"
TEXT_LABEL = "#607090"

WHITE = "#f0f4f8"

# ── Matplotlib colours (for plots) ──────────────────────────────────────────

MPL_BG = BG_DARKEST
MPL_FACE = BG_DARK
MPL_GRID = "#101828"
MPL_TEXT = TEXT_PRIMARY

ORBIT_INITIAL = CYAN
ORBIT_INITIAL_GLOW = CYAN_GLOW
ORBIT_TARGET = AMBER
ORBIT_TARGET_GLOW = AMBER_GLOW
ORBIT_TRANSFER = "#b388ff"       # soft violet for transfer arcs
ORBIT_TRANSFER_GLOW = "#9060ee"
ORBIT_TRANSFER_2 = "#ff80ab"     # pink for bi-elliptic second arc
BURN_MARKER = RED
EARTH_WIRE = "#1a6fa8"
EARTH_WIRE_GLOW = "#0d3a5c"
EARTH_FILL = "#020810"

# ── Qt Stylesheet ───────────────────────────────────────────────────────────

QSS = f"""
/* ── Base ── */
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: "Consolas", "SF Mono", "Fira Code", "Source Code Pro", monospace;
    font-size: 12px;
}}

/* ── Labels ── */
QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
    padding: 1px;
}}

QLabel[class="heading"] {{
    color: {AMBER};
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
    color: {AMBER};
    font-size: 11px;
    font-weight: bold;
    border-bottom: 1px solid {GRID_DIM};
    padding-bottom: 3px;
    margin-top: 6px;
}}

/* ── Group Boxes ── */
QGroupBox {{
    border: 1px solid {GRID_DIM};
    border-radius: 0px;
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
    color: {AMBER};
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 1px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {BG_CARD};
    border: 1px solid {GRID_DIM};
    border-radius: 0px;
    color: {AMBER};
    padding: 6px 14px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}

QPushButton:hover {{
    border-color: {AMBER_DIM};
    background-color: {AMBER_FAINT};
    color: {AMBER_BRIGHT};
}}

QPushButton:pressed {{
    background-color: {AMBER_DIM};
    color: {BG_DARKEST};
}}

QPushButton[class="preset"] {{
    padding: 5px 10px;
    font-size: 10px;
    text-align: left;
    padding-left: 12px;
    border-left: 2px solid {AMBER_DIM};
    color: {TEXT_PRIMARY};
}}

QPushButton[class="preset"]:hover {{
    border-left: 2px solid {AMBER};
    color: {AMBER_BRIGHT};
    background-color: {AMBER_FAINT};
}}

QPushButton[class="action"] {{
    border: 1px solid {AMBER_DIM};
    color: {AMBER};
    padding: 4px 12px;
    font-size: 10px;
}}

QPushButton[class="action"]:hover {{
    border-color: {AMBER};
    background-color: {AMBER_FAINT};
}}

QPushButton[class="danger"] {{
    border: 1px solid {RED_DIM};
    color: {RED};
    padding: 4px 12px;
    font-size: 10px;
}}

QPushButton[class="danger"]:hover {{
    border-color: {RED};
    background-color: #1a0008;
}}

/* ── Tab Bar ── */
QTabWidget::pane {{
    border: 1px solid {GRID_DIM};
    border-top: none;
    background-color: {BG_DARK};
}}

QTabBar {{
    background-color: {BG_DARKEST};
}}

QTabBar::tab {{
    background-color: {BG_PANEL};
    color: {TEXT_DIM};
    border: 1px solid {GRID_DIM};
    border-bottom: none;
    padding: 6px 16px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1px;
    min-width: 80px;
}}

QTabBar::tab:selected {{
    background-color: {BG_DARK};
    color: {AMBER};
    border-bottom: 2px solid {AMBER};
}}

QTabBar::tab:hover:!selected {{
    color: {AMBER_DIM};
    background-color: {BG_CARD};
}}

/* ── Scroll Area ── */
QScrollArea {{
    border: none;
    background-color: {BG_DARK};
}}

QScrollBar:vertical {{
    background-color: {BG_PANEL};
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {GRID_MID};
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {AMBER_DIM};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Separators ── */
QFrame[class="separator"] {{
    background-color: {GRID_DIM};
    max-height: 1px;
    min-height: 1px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {GRID_DIM};
    width: 1px;
    height: 1px;
}}

/* ── Status Bar ── */
QStatusBar {{
    background-color: {BG_DARKEST};
    color: {TEXT_DIM};
    border-top: 1px solid {GRID_DIM};
    font-size: 10px;
}}

/* ── SpinBox (for direct entry dialogs) ── */
QSpinBox, QDoubleSpinBox {{
    background-color: {BG_INPUT};
    border: 1px solid {GRID_DIM};
    border-radius: 0px;
    color: {AMBER_BRIGHT};
    padding: 3px 6px;
    font-size: 12px;
    selection-background-color: {AMBER_DIM};
}}
"""
