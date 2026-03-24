"""
VESPER main application — PySide6 GUI.

Layout:
  ┌─── Custom Title Bar ─ VESPER ─── [─] [□] [×] ─────────────────┐
  │ ┌──────────────┬───────────────────────────────────────────────┐│
  │ │  LEFT PANEL  │ [ANALYSIS] [TRADE] [COMPARE] [INFO]          ││
  │ │              │ ┌──────────────────────────────────────────┐  ││
  │ │  Parameters  │ │                                          │  ││
  │ │  Presets     │ │         Tab content area                 │  ││
  │ │  Results     │ │                                          │  ││
  │ │  Scenarios   │ └──────────────────────────────────────────┘  ││
  │ └──────────────┴───────────────────────────────────────────────┘│
  └────────────────────────────────────────────────────────────────┘

Features:
  - Custom frameless title bar (Evangelion style)
  - Evangelion segmented-bar sliders
  - Tabbed right panel: Analysis / Trade Study / Comparison / Info
  - Scenario save/compare
  - Expanded preset library
  - Method explanation panel
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QScrollArea, QTextEdit,
    QPushButton, QFrame, QSplitter, QSizePolicy, QTabWidget,
    QInputDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from vesper.styles import (
    QSS, CYAN, CYAN_DIM, AMBER, AMBER_BRIGHT, AMBER_DIM,
    GREEN, RED, TEXT_DIM, TEXT_PRIMARY, TEXT_LABEL, TEXT_BRIGHT,
    BG_PANEL, BG_DARK, BG_DARKEST, GRID_DIM,
)
from vesper.mechanics import (
    compute_transfers, compare_plane_changes, compute_mission_chain,
    TransferResult, PlaneChangeStrategy, MissionLeg,
)
from vesper.plotting import (
    create_orbit_figure, create_trade_figure,
    update_orbit_figure, update_trade_figure,
    update_trade_inclination, update_trade_time,
    update_plane_change_chart, update_mission_chain_figure,
)
from vesper.widgets import HudSlider, HudTitleBar, ScenarioTable
from vesper.scenarios import ScenarioManager
from vesper.info_text import INFO_SECTIONS


class VesperWindow(QMainWindow):
    """Main VESPER application window."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setStyleSheet(QSS)

        self._scenario_mgr = ScenarioManager()

        self._build_ui()
        self._connect_signals()

        # Debounce timer
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(30)
        self._update_timer.timeout.connect(self._update_all)

        # Resize edge tracking
        self._resize_edge = None
        self._resize_start = None
        self._resize_geom = None
        self.setMouseTracking(True)

        self._update_all()

    # ── UI Construction ─────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Custom title bar ──
        self._titlebar = HudTitleBar(
            self, title="VESPER",
            subtitle="ORBITAL TRANSFER ANALYSIS"
        )
        root.addWidget(self._titlebar)

        # ── Main content area ──
        content = QWidget()
        main_layout = QHBoxLayout(content)
        main_layout.setContentsMargins(4, 2, 4, 4)
        main_layout.setSpacing(4)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ── Left Panel ──
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setMaximumWidth(340)
        left_scroll.setMinimumWidth(280)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(3)

        # Inputs
        left_layout.addWidget(self._build_inputs())
        left_layout.addWidget(self._sep())

        # Presets (expanded)
        left_layout.addWidget(self._build_presets())
        left_layout.addWidget(self._sep())

        # Results
        left_layout.addWidget(self._build_results())
        left_layout.addWidget(self._sep())

        # Scenario section
        left_layout.addWidget(self._build_scenario_controls())

        left_layout.addStretch()

        # Footer
        footer = QLabel(
            "TWO-BODY KEPLERIAN  \u2502  EARTH-CENTRED"
        )
        footer.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 8px; padding: 4px;"
        )
        footer.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(footer)

        left_scroll.setWidget(left)
        splitter.addWidget(left_scroll)

        # ── Right Panel (tabbed) ──
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(False)

        # Tab 0: Analysis (orbit + trade dv)
        self._tabs.addTab(self._build_analysis_tab(), "ANALYSIS")

        # Tab 1: Trade Study (multi-parameter)
        self._tabs.addTab(self._build_trade_tab(), "TRADE STUDY")

        # Tab 2: Comparison
        self._tabs.addTab(self._build_compare_tab(), "COMPARE")

        # Tab 3: Info
        self._tabs.addTab(self._build_info_tab(), "INFO")

        splitter.addWidget(self._tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 1080])

        root.addWidget(content)

        # Status bar
        self.statusBar().showMessage("VESPER v0.2")

    def _sep(self):
        sep = QFrame()
        sep.setProperty("class", "separator")
        sep.setFrameShape(QFrame.HLine)
        return sep

    # ── Input Panel ─────────────────────────────────────────────────────

    def _build_inputs(self):
        group = QGroupBox("ORBIT PARAMETERS")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)
        layout.setContentsMargins(6, 14, 6, 6)

        self.slider_init = HudSlider(
            label="INITIAL ALTITUDE", min_val=150, max_val=10000,
            value=400, step=10, decimals=0, suffix=" km", accent=CYAN,
        )
        layout.addWidget(self.slider_init)

        self.slider_target = HudSlider(
            label="TARGET ALTITUDE", min_val=150, max_val=100000,
            value=35786, step=1, decimals=0, suffix=" km", accent=AMBER,
        )
        layout.addWidget(self.slider_target)

        self.slider_inc = HudSlider(
            label="INCLINATION CHANGE", min_val=0.0, max_val=90.0,
            value=0.0, step=0.5, decimals=1, suffix="\u00b0", accent=AMBER,
        )
        layout.addWidget(self.slider_inc)

        return group

    # ── Presets (expanded) ──────────────────────────────────────────────

    def _build_presets(self):
        group = QGroupBox("PRESET LIBRARY")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        presets = [
            ("LEO 300 km circular", 300, 300, 0.0),
            ("LEO \u2192 LEO   400 \u2192 800 km", 400, 800, 0.0),
            ("LEO \u2192 MEO   400 \u2192 20200 km", 400, 20200, 0.0),
            ("LEO \u2192 GEO   400 \u2192 35786 km", 400, 35786, 0.0),
            ("LEO \u2192 GEO + 28.5\u00b0", 400, 35786, 28.5),
            ("ISS \u2192 GTO   420 \u2192 35786 km", 420, 35786, 0.0),
            ("ISS \u2192 HEO   420 \u2192 45000 km", 420, 45000, 0.0),
            ("LEO \u2192 GEO + 51.6\u00b0 (ISS)", 400, 35786, 51.6),
            ("500 km \u2192 MEO (GPS)", 500, 20200, 0.0),
            ("GTO-style  250 \u2192 35786 km", 250, 35786, 0.0),
        ]

        for label, init, target, inc in presets:
            btn = QPushButton(label)
            btn.setProperty("class", "preset")
            btn.clicked.connect(
                lambda checked, i=init, t=target, d=inc:
                    self._apply_preset(i, t, d)
            )
            layout.addWidget(btn)

        return group

    # ── Results Panel ──────────────────────────────────────────────────

    def _build_results(self):
        group = QGroupBox("TRANSFER COMPARISON")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        self.results_widgets = {}
        for slot in range(4):
            card = QWidget()
            cl = QGridLayout(card)
            cl.setContentsMargins(4, 4, 4, 4)
            cl.setSpacing(2)

            name_label = QLabel("")
            name_label.setProperty("class", "section")
            cl.addWidget(name_label, 0, 0, 1, 2)

            dv_total_label = QLabel("")
            dv_total_label.setProperty("class", "value")
            cl.addWidget(dv_total_label, 1, 0)

            dv_unit = QLabel("m/s total \u0394v")
            dv_unit.setProperty("class", "unit")
            cl.addWidget(dv_unit, 1, 1)

            burns_label = QLabel("")
            burns_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
            cl.addWidget(burns_label, 2, 0, 1, 2)

            time_label = QLabel("")
            time_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
            cl.addWidget(time_label, 3, 0, 1, 2)

            best_label = QLabel("")
            best_label.setProperty("class", "best")
            cl.addWidget(best_label, 4, 0, 1, 2)

            self.results_widgets[slot] = {
                "card": card, "name": name_label,
                "dv_total": dv_total_label, "burns": burns_label,
                "time": time_label, "best": best_label,
            }
            layout.addWidget(card)

        return group

    # ── Scenario Controls ──────────────────────────────────────────────

    def _build_scenario_controls(self):
        group = QGroupBox("SCENARIOS")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        btn_row = QHBoxLayout()
        self._btn_save = QPushButton("SAVE CURRENT")
        self._btn_save.setProperty("class", "action")
        self._btn_save.clicked.connect(self._save_scenario)
        btn_row.addWidget(self._btn_save)

        self._btn_clear = QPushButton("CLEAR ALL")
        self._btn_clear.setProperty("class", "danger")
        self._btn_clear.clicked.connect(self._clear_scenarios)
        btn_row.addWidget(self._btn_clear)
        layout.addLayout(btn_row)

        self._scenario_count_label = QLabel("0 / 8 scenarios saved")
        self._scenario_count_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px;"
        )
        layout.addWidget(self._scenario_count_label)

        return group

    # ── Analysis Tab (orbit + trade dv) ────────────────────────────────

    def _build_analysis_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        self._orbit_fig, self._orbit_ax = create_orbit_figure()
        self.orbit_canvas = FigureCanvas(self._orbit_fig)
        self.orbit_canvas.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        layout.addWidget(self.orbit_canvas, stretch=3)

        self._trade_fig, self._trade_ax = create_trade_figure()
        self.trade_canvas = FigureCanvas(self._trade_fig)
        self.trade_canvas.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        layout.addWidget(self.trade_canvas, stretch=1)

        return tab

    # ── Trade Study Tab (multi-parameter) ──────────────────────────────

    def _build_trade_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Sub-tabs for different trade study types
        self._trade_tabs = QTabWidget()
        self._trade_tabs.setDocumentMode(True)

        # Inclination sweep
        self._inc_fig, self._inc_ax = create_trade_figure()
        self._inc_canvas = FigureCanvas(self._inc_fig)
        self._trade_tabs.addTab(self._inc_canvas, "\u0394v vs INCLINATION")

        # Transfer time
        self._time_fig, self._time_ax = create_trade_figure()
        self._time_canvas = FigureCanvas(self._time_fig)
        self._trade_tabs.addTab(self._time_canvas, "TIME vs ALTITUDE")

        # Plane change comparison (wider left margin for bar labels)
        self._pc_fig, self._pc_ax = create_trade_figure(left_margin=0.30)
        self._pc_canvas = FigureCanvas(self._pc_fig)
        self._trade_tabs.addTab(self._pc_canvas, "PLANE CHANGE")

        # Mission chain
        self._chain_fig, self._chain_ax = create_trade_figure()
        self._chain_canvas = FigureCanvas(self._chain_fig)
        self._trade_tabs.addTab(self._chain_canvas, "MISSION CHAIN")

        layout.addWidget(self._trade_tabs)

        return tab

    # ── Compare Tab ────────────────────────────────────────────────────

    def _build_compare_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel("SCENARIO COMPARISON")
        header.setStyleSheet(
            f"color: {AMBER}; font-size: 12px; font-weight: bold;"
            f" letter-spacing: 2px;"
        )
        layout.addWidget(header)

        desc = QLabel(
            "Save scenarios from the left panel, then compare them here.\n"
            "Double-click a row to remove it."
        )
        desc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px;")
        layout.addWidget(desc)

        self._scenario_table = ScenarioTable()
        self._scenario_table.removeRequested.connect(self._remove_scenario)
        layout.addWidget(self._scenario_table, stretch=1)

        return tab

    # ── Info Tab ───────────────────────────────────────────────────────

    def _build_info_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        page_title = QLabel("METHOD REFERENCE")
        page_title.setStyleSheet(
            f"color: {AMBER}; font-size: 14px; font-weight: bold;"
            f" letter-spacing: 3px;"
        )
        layout.addWidget(page_title)

        for section in INFO_SECTIONS:
            title_lbl = QLabel(section["title"])
            title_lbl.setStyleSheet(
                f"color: {AMBER_BRIGHT}; font-size: 11px;"
                f" font-weight: bold; letter-spacing: 1px;"
                f" border-bottom: 1px solid {GRID_DIM};"
                f" padding-bottom: 4px; margin-top: 8px;"
            )
            layout.addWidget(title_lbl)

            content_lbl = QLabel(section["content"])
            content_lbl.setWordWrap(True)
            content_lbl.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: 10px;"
                f" line-height: 1.4; padding: 4px 0;"
                f" font-family: Consolas, monospace;"
            )
            layout.addWidget(content_lbl)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ── Signals ─────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.slider_init.valueChanged.connect(self._schedule_update)
        self.slider_target.valueChanged.connect(self._schedule_update)
        self.slider_inc.valueChanged.connect(self._schedule_update)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._trade_tabs.currentChanged.connect(self._on_trade_tab_changed)

    def _schedule_update(self):
        self._update_timer.start()

    def _on_tab_changed(self, index):
        if index == 1:
            self._update_trade_studies()
        elif index == 2:
            self._update_compare_tab()

    def _on_trade_tab_changed(self, index):
        self._update_trade_studies()

    # ── Presets ─────────────────────────────────────────────────────────

    def _apply_preset(self, init_alt, target_alt, inc_deg):
        for s in (self.slider_init, self.slider_target, self.slider_inc):
            s.blockSignals(True)
        self.slider_init.setValue(init_alt)
        self.slider_target.setValue(target_alt)
        self.slider_inc.setValue(inc_deg)
        for s in (self.slider_init, self.slider_target, self.slider_inc):
            s.blockSignals(False)
        self._update_all()

    # ── Scenario Management ────────────────────────────────────────────

    def _save_scenario(self):
        alt_i = self.slider_init.value()
        alt_t = self.slider_target.value()
        inc = self.slider_inc.value()

        # Auto-generate a name
        default_name = f"{int(alt_i)}\u2192{int(alt_t)} km"
        if inc > 0:
            default_name += f" +{inc:.1f}\u00b0"

        name, ok = QInputDialog.getText(
            self, "Save Scenario", "Scenario name:", text=default_name
        )
        if not ok or not name:
            return

        self._scenario_mgr.save(name, alt_i, alt_t, inc)
        self._update_scenario_count()
        self._update_compare_tab()

    def _remove_scenario(self, index):
        self._scenario_mgr.remove(index)
        self._update_scenario_count()
        self._update_compare_tab()

    def _clear_scenarios(self):
        self._scenario_mgr.clear()
        self._update_scenario_count()
        self._update_compare_tab()

    def _update_scenario_count(self):
        n = self._scenario_mgr.count
        self._scenario_count_label.setText(f"{n} / 8 scenarios saved")

    def _update_compare_tab(self):
        self._scenario_table.set_scenarios(self._scenario_mgr.scenarios)

    # ── Core Update ─────────────────────────────────────────────────────

    def _update_all(self):
        alt_init = self.slider_init.value()
        alt_target = self.slider_target.value()
        delta_inc = self.slider_inc.value()

        if alt_init == alt_target:
            self._clear_results()
            return

        transfers = compute_transfers(alt_init, alt_target, delta_inc)
        self._update_results(transfers)

        # Update analysis tab (always)
        update_orbit_figure(self._orbit_ax, alt_init, alt_target, transfers)
        self.orbit_canvas.draw_idle()

        update_trade_figure(self._trade_ax, alt_init, alt_target, delta_inc)
        self.trade_canvas.draw_idle()

        # Update trade studies if visible
        if self._tabs.currentIndex() == 1:
            self._update_trade_studies()

        self.statusBar().showMessage(
            f"INIT: {alt_init:.0f} km  \u2502  TARGET: {alt_target:.0f} km"
            f"  \u2502  \u0394i: {delta_inc:.1f}\u00b0  \u2502  "
            f"{len(transfers)} transfer(s)"
        )

    def _update_trade_studies(self):
        alt_init = self.slider_init.value()
        alt_target = self.slider_target.value()
        delta_inc = self.slider_inc.value()

        idx = self._trade_tabs.currentIndex()

        if idx == 0:
            update_trade_inclination(self._inc_ax, alt_init, alt_target)
            self._inc_canvas.draw_idle()
        elif idx == 1:
            update_trade_time(self._time_ax, alt_init, alt_target)
            self._time_canvas.draw_idle()
        elif idx == 2:
            strategies = compare_plane_changes(alt_init, alt_target, delta_inc)
            update_plane_change_chart(self._pc_ax, strategies)
            self._pc_canvas.draw_idle()
        elif idx == 3:
            # Demo mission chain based on current params
            chain_spec = [
                ("LEO raise", 400, alt_init, 0.0),
            ]
            if alt_init != alt_target:
                chain_spec.append(("Main transfer", alt_init, alt_target, 0.0))
            if delta_inc > 0:
                chain_spec.append(("Plane change", alt_target, alt_target, delta_inc))
            legs, total_dv, total_time = compute_mission_chain(chain_spec)
            # Filter out legs with same init/target (dv=0)
            legs = [l for l in legs if l.result.delta_v_total > 0.1]
            total_dv = sum(l.result.delta_v_total for l in legs)
            total_time = sum(l.result.transfer_time for l in legs)
            update_mission_chain_figure(
                self._chain_ax, legs, total_dv, total_time
            )
            self._chain_canvas.draw_idle()

    def _update_results(self, transfers: list[TransferResult]):
        for slot in range(4):
            w = self.results_widgets[slot]
            if slot < len(transfers):
                t = transfers[slot]
                w["card"].setVisible(True)
                w["name"].setText(t.name.upper())
                w["dv_total"].setText(f"{t.delta_v_total:.1f}")

                if t.delta_v_3 is not None:
                    w["burns"].setText(
                        f"B1: {t.delta_v_1:.1f}  B2: {t.delta_v_2:.1f}  "
                        f"B3: {t.delta_v_3:.1f} m/s"
                    )
                else:
                    w["burns"].setText(
                        f"B1: {t.delta_v_1:.1f}  B2: {t.delta_v_2:.1f} m/s"
                    )
                w["time"].setText(f"Transfer: {_fmt_time(t.transfer_time)}")

                if slot == 0:
                    w["best"].setText("\u2713 LOWEST \u0394v")
                    w["dv_total"].setStyleSheet(
                        f"color: {GREEN}; font-size: 18px; font-weight: bold;"
                    )
                else:
                    w["best"].setText("")
                    w["dv_total"].setStyleSheet(
                        f"color: {TEXT_PRIMARY}; font-size: 18px;"
                        f" font-weight: bold;"
                    )
            else:
                w["card"].setVisible(False)

    def _clear_results(self):
        for slot in range(4):
            self.results_widgets[slot]["card"].setVisible(False)

    # ── Window resize from edges ────────────────────────────────────────

    _EDGE_MARGIN = 6

    def _edge_at(self, pos):
        """Detect which edge the mouse is near for resize."""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = self._EDGE_MARGIN
        edge = ""
        if y < m:
            edge += "t"
        elif y > h - m:
            edge += "b"
        if x < m:
            edge += "l"
        elif x > w - m:
            edge += "r"
        return edge or None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._edge_at(event.position())
            if edge:
                self._resize_edge = edge
                self._resize_start = event.globalPosition().toPoint()
                self._resize_geom = self.geometry()

    def mouseMoveEvent(self, event):
        if self._resize_edge and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._resize_start
            g = self._resize_geom
            x, y, w, h = g.x(), g.y(), g.width(), g.height()
            min_w, min_h = self.minimumWidth(), self.minimumHeight()

            if "r" in self._resize_edge:
                w = max(min_w, g.width() + delta.x())
            if "b" in self._resize_edge:
                h = max(min_h, g.height() + delta.y())
            if "l" in self._resize_edge:
                new_w = max(min_w, g.width() - delta.x())
                x = g.x() + g.width() - new_w
                w = new_w
            if "t" in self._resize_edge:
                new_h = max(min_h, g.height() - delta.y())
                y = g.y() + g.height() - new_h
                h = new_h

            self.setGeometry(x, y, w, h)
        else:
            # Update cursor for edge detection
            edge = self._edge_at(event.position())
            if edge in ("l", "r"):
                self.setCursor(Qt.SizeHorCursor)
            elif edge in ("t", "b"):
                self.setCursor(Qt.SizeVerCursor)
            elif edge in ("tl", "br"):
                self.setCursor(Qt.SizeFDiagCursor)
            elif edge in ("tr", "bl"):
                self.setCursor(Qt.SizeBDiagCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._resize_edge = None
        self._resize_start = None
        self._resize_geom = None


def _fmt_time(seconds: float) -> str:
    h = seconds / 3600.0
    if h < 1:
        return f"{seconds / 60:.1f} min"
    elif h < 48:
        return f"{h:.1f} hr"
    return f"{h / 24:.1f} days"


def run():
    """Entry point for the VESPER application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = VesperWindow()
    window.show()
    sys.exit(app.exec())
