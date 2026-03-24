"""
VESPER main application — PySide6 GUI.

Layout:
  ┌──────────────┬────────────────────────────────────────┐
  │  LEFT PANEL  │            MAIN AREA                   │
  │              │  ┌──────────────────────────────────┐  │
  │  Inputs      │  │       Orbit Visualisation        │  │
  │  Presets     │  │                                  │  │
  │  Results     │  └──────────────────────────────────┘  │
  │              │  ┌──────────────────────────────────┐  │
  │              │  │       Trade Study Plot           │  │
  │              │  └──────────────────────────────────┘  │
  └──────────────┴────────────────────────────────────────┘
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QSlider, QSpinBox, QDoubleSpinBox,
    QPushButton, QFrame, QSplitter, QStatusBar, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from vesper.styles import QSS, CYAN, AMBER, GREEN, RED, TEXT_DIM, TEXT_PRIMARY
from vesper.mechanics import (
    compute_transfers, hohmann_transfer, bielliptic_transfer,
    alt_to_radius, TransferResult,
)
from vesper.plotting import create_orbit_figure, create_trade_figure


class VesperWindow(QMainWindow):
    """Main VESPER application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VESPER — Visual Engine for Spaceflight Planning, Exploration, and Rendezvous")
        self.setMinimumSize(1100, 750)
        self.resize(1300, 850)
        self.setStyleSheet(QSS)

        self._build_ui()
        self._connect_signals()

        # Debounce timer to avoid recomputing on every slider tick
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(50)
        self._update_timer.timeout.connect(self._update_all)

        # Initial computation
        self._update_all()

    # ── UI Construction ─────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ── Left Panel ──
        left = QWidget()
        left.setMaximumWidth(320)
        left.setMinimumWidth(260)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(4)

        # Title
        title = QLabel("VESPER")
        title.setProperty("class", "heading")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Consolas", 16, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {CYAN}; letter-spacing: 6px; padding: 8px 0;")
        left_layout.addWidget(title)

        subtitle = QLabel("ORBITAL TRANSFER ANALYSIS")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 3px;")
        left_layout.addWidget(subtitle)

        left_layout.addWidget(self._make_separator())

        # Inputs
        left_layout.addWidget(self._build_inputs())

        left_layout.addWidget(self._make_separator())

        # Presets
        left_layout.addWidget(self._build_presets())

        left_layout.addWidget(self._make_separator())

        # Results
        left_layout.addWidget(self._build_results())

        left_layout.addStretch()

        # Status line
        status_label = QLabel("TWO-BODY KEPLERIAN  |  EARTH-CENTRED  |  DEMO")
        status_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; padding: 4px;")
        status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(status_label)

        splitter.addWidget(left)

        # ── Right Panel (plots) ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(2, 2, 2, 2)
        right_layout.setSpacing(4)

        # Orbit view canvas
        self.orbit_canvas = FigureCanvas(create_orbit_figure(400, 35786, []))
        self.orbit_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(self.orbit_canvas, stretch=3)

        # Trade study canvas
        self.trade_canvas = FigureCanvas(create_trade_figure(400, 35786))
        self.trade_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(self.trade_canvas, stretch=1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 1000])

        # Status bar
        self.statusBar().showMessage("VESPER v0.1 — DEMO")

    def _make_separator(self):
        sep = QFrame()
        sep.setProperty("class", "separator")
        sep.setFrameShape(QFrame.HLine)
        return sep

    def _build_inputs(self):
        group = QGroupBox("ORBIT PARAMETERS")
        layout = QGridLayout(group)
        layout.setSpacing(6)

        # Initial altitude
        layout.addWidget(QLabel("INITIAL ALT"), 0, 0)
        self.spin_init = QSpinBox()
        self.spin_init.setRange(150, 100000)
        self.spin_init.setValue(400)
        self.spin_init.setSuffix(" km")
        self.spin_init.setSingleStep(50)
        layout.addWidget(self.spin_init, 0, 1)

        self.slider_init = QSlider(Qt.Horizontal)
        self.slider_init.setRange(150, 10000)
        self.slider_init.setValue(400)
        layout.addWidget(self.slider_init, 1, 0, 1, 2)

        # Target altitude
        layout.addWidget(QLabel("TARGET ALT"), 2, 0)
        self.spin_target = QSpinBox()
        self.spin_target.setRange(150, 100000)
        self.spin_target.setValue(35786)
        self.spin_target.setSuffix(" km")
        self.spin_target.setSingleStep(100)
        layout.addWidget(self.spin_target, 2, 1)

        self.slider_target = QSlider(Qt.Horizontal)
        self.slider_target.setRange(150, 100000)
        self.slider_target.setValue(35786)
        layout.addWidget(self.slider_target, 3, 0, 1, 2)

        # Inclination change
        layout.addWidget(QLabel("INCL. CHANGE"), 4, 0)
        self.spin_inc = QDoubleSpinBox()
        self.spin_inc.setRange(0.0, 90.0)
        self.spin_inc.setValue(0.0)
        self.spin_inc.setSuffix(" \u00b0")
        self.spin_inc.setSingleStep(1.0)
        self.spin_inc.setDecimals(1)
        layout.addWidget(self.spin_inc, 4, 1)

        self.slider_inc = QSlider(Qt.Horizontal)
        self.slider_inc.setRange(0, 900)  # 0.0 to 90.0 in tenths
        self.slider_inc.setValue(0)
        layout.addWidget(self.slider_inc, 5, 0, 1, 2)

        return group

    def _build_presets(self):
        group = QGroupBox("PRESETS")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        presets = [
            ("LEO \u2192 LEO  (400 \u2192 800 km)", 400, 800, 0.0),
            ("LEO \u2192 MEO  (400 \u2192 20200 km)", 400, 20200, 0.0),
            ("LEO \u2192 GEO  (400 \u2192 35786 km)", 400, 35786, 0.0),
            ("LEO \u2192 GEO + 28\u00b0", 400, 35786, 28.5),
            ("ISS \u2192 HEO  (420 \u2192 45000 km)", 420, 45000, 0.0),
        ]

        for label, init, target, inc in presets:
            btn = QPushButton(label)
            btn.setProperty("class", "preset")
            btn.clicked.connect(
                lambda checked, i=init, t=target, d=inc: self._apply_preset(i, t, d)
            )
            layout.addWidget(btn)

        return group

    def _build_results(self):
        group = QGroupBox("TRANSFER COMPARISON")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        self.results_widgets = {}

        # We'll show up to 4 transfer results
        for slot in range(4):
            card = QWidget()
            card_layout = QGridLayout(card)
            card_layout.setContentsMargins(4, 4, 4, 4)
            card_layout.setSpacing(2)

            name_label = QLabel("")
            name_label.setProperty("class", "section")
            card_layout.addWidget(name_label, 0, 0, 1, 2)

            dv_total_label = QLabel("")
            dv_total_label.setProperty("class", "value")
            card_layout.addWidget(dv_total_label, 1, 0)

            dv_unit = QLabel("m/s total \u0394v")
            dv_unit.setProperty("class", "unit")
            card_layout.addWidget(dv_unit, 1, 1)

            burns_label = QLabel("")
            burns_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
            card_layout.addWidget(burns_label, 2, 0, 1, 2)

            time_label = QLabel("")
            time_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
            card_layout.addWidget(time_label, 3, 0, 1, 2)

            best_label = QLabel("")
            best_label.setProperty("class", "best")
            card_layout.addWidget(best_label, 4, 0, 1, 2)

            self.results_widgets[slot] = {
                "card": card,
                "name": name_label,
                "dv_total": dv_total_label,
                "burns": burns_label,
                "time": time_label,
                "best": best_label,
            }

            layout.addWidget(card)

        return group

    # ── Signal Wiring ───────────────────────────────────────────────────

    def _connect_signals(self):
        # Sync sliders ↔ spinboxes
        self.slider_init.valueChanged.connect(self.spin_init.setValue)
        self.spin_init.valueChanged.connect(self.slider_init.setValue)

        self.slider_target.valueChanged.connect(self.spin_target.setValue)
        self.spin_target.valueChanged.connect(self.slider_target.setValue)

        self.slider_inc.valueChanged.connect(
            lambda v: self.spin_inc.setValue(v / 10.0))
        self.spin_inc.valueChanged.connect(
            lambda v: self.slider_inc.setValue(int(v * 10)))

        # Trigger update on any value change (debounced)
        self.spin_init.valueChanged.connect(self._schedule_update)
        self.spin_target.valueChanged.connect(self._schedule_update)
        self.spin_inc.valueChanged.connect(self._schedule_update)

    def _schedule_update(self):
        self._update_timer.start()

    # ── Preset Application ──────────────────────────────────────────────

    def _apply_preset(self, init_alt, target_alt, inc_deg):
        self.spin_init.blockSignals(True)
        self.slider_init.blockSignals(True)
        self.spin_target.blockSignals(True)
        self.slider_target.blockSignals(True)
        self.spin_inc.blockSignals(True)
        self.slider_inc.blockSignals(True)

        self.spin_init.setValue(init_alt)
        self.slider_init.setValue(min(init_alt, self.slider_init.maximum()))
        self.spin_target.setValue(target_alt)
        self.slider_target.setValue(min(target_alt, self.slider_target.maximum()))
        self.spin_inc.setValue(inc_deg)
        self.slider_inc.setValue(int(inc_deg * 10))

        self.spin_init.blockSignals(False)
        self.slider_init.blockSignals(False)
        self.spin_target.blockSignals(False)
        self.slider_target.blockSignals(False)
        self.spin_inc.blockSignals(False)
        self.slider_inc.blockSignals(False)

        self._update_all()

    # ── Core Update ─────────────────────────────────────────────────────

    def _update_all(self):
        alt_init = self.spin_init.value()
        alt_target = self.spin_target.value()
        delta_inc = self.spin_inc.value()

        if alt_init == alt_target:
            self._clear_results()
            return

        # Compute transfers
        transfers = compute_transfers(alt_init, alt_target, delta_inc)

        # Update results panel
        self._update_results(transfers)

        # Update orbit plot
        old_fig = self.orbit_canvas.figure
        new_fig = create_orbit_figure(alt_init, alt_target, transfers)
        self.orbit_canvas.figure = new_fig
        new_fig.set_canvas(self.orbit_canvas)
        old_fig.clear()
        self.orbit_canvas.draw_idle()

        # Update trade study plot
        old_trade = self.trade_canvas.figure
        new_trade = create_trade_figure(alt_init, alt_target, delta_inc)
        self.trade_canvas.figure = new_trade
        new_trade.set_canvas(self.trade_canvas)
        old_trade.clear()
        self.trade_canvas.draw_idle()

        # Status
        self.statusBar().showMessage(
            f"INIT: {alt_init} km  |  TARGET: {alt_target} km  |  "
            f"\u0394i: {delta_inc:.1f}\u00b0  |  "
            f"{len(transfers)} transfer(s) computed"
        )

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

                w["time"].setText(f"Transfer: {self._format_time(t.transfer_time)}")

                if slot == 0:
                    w["best"].setText("\u2713 LOWEST \u0394v")
                    w["dv_total"].setStyleSheet(f"color: {GREEN}; font-size: 18px; font-weight: bold;")
                else:
                    w["best"].setText("")
                    w["dv_total"].setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 18px; font-weight: bold;")
            else:
                w["card"].setVisible(False)

    def _clear_results(self):
        for slot in range(4):
            self.results_widgets[slot]["card"].setVisible(False)

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format transfer time for display."""
        hours = seconds / 3600.0
        if hours < 1:
            return f"{seconds / 60:.1f} min"
        elif hours < 48:
            return f"{hours:.1f} hr"
        else:
            days = hours / 24.0
            return f"{days:.1f} days"


def run():
    """Entry point for the VESPER application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Consistent cross-platform base style

    window = VesperWindow()
    window.show()
    sys.exit(app.exec())
