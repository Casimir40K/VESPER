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

Performance: figures are created once; axes are cleared and redrawn in-place.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel,
    QPushButton, QFrame, QSplitter, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from vesper.styles import (
    QSS, CYAN, CYAN_DIM, AMBER, GREEN, RED, TEXT_DIM, TEXT_PRIMARY,
    BG_PANEL, GRID_DIM,
)
from vesper.mechanics import compute_transfers, TransferResult
from vesper.plotting import (
    create_orbit_figure, create_trade_figure,
    update_orbit_figure, update_trade_figure,
)
from vesper.widgets import HudSlider


class VesperWindow(QMainWindow):
    """Main VESPER application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "VESPER — Visual Engine for Spaceflight Planning, "
            "Exploration, and Rendezvous"
        )
        self.setMinimumSize(1100, 750)
        self.resize(1300, 850)
        self.setStyleSheet(QSS)

        self._build_ui()
        self._connect_signals()

        # Debounce timer — 30 ms for responsive feel
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(30)
        self._update_timer.timeout.connect(self._update_all)

        # Initial draw
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
        left.setMaximumWidth(330)
        left.setMinimumWidth(270)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(4)

        # Title
        title = QLabel("VESPER")
        title.setProperty("class", "heading")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Consolas", 16, QFont.Bold))
        title.setStyleSheet(
            f"color: {CYAN}; letter-spacing: 6px; padding: 8px 0;"
        )
        left_layout.addWidget(title)

        subtitle = QLabel("ORBITAL TRANSFER ANALYSIS")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 3px;"
        )
        left_layout.addWidget(subtitle)

        left_layout.addWidget(self._sep())

        # Inputs — custom HUD sliders
        left_layout.addWidget(self._build_inputs())

        left_layout.addWidget(self._sep())

        # Presets
        left_layout.addWidget(self._build_presets())

        left_layout.addWidget(self._sep())

        # Results
        left_layout.addWidget(self._build_results())

        left_layout.addStretch()

        status_label = QLabel(
            "TWO-BODY KEPLERIAN  \u2502  EARTH-CENTRED  \u2502  DEMO"
        )
        status_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px; padding: 4px;"
        )
        status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(status_label)

        splitter.addWidget(left)

        # ── Right Panel (plots) ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(2, 2, 2, 2)
        right_layout.setSpacing(4)

        # Create figures ONCE — reuse via update functions
        self._orbit_fig, self._orbit_ax = create_orbit_figure()
        self.orbit_canvas = FigureCanvas(self._orbit_fig)
        self.orbit_canvas.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        right_layout.addWidget(self.orbit_canvas, stretch=3)

        self._trade_fig, self._trade_ax = create_trade_figure()
        self.trade_canvas = FigureCanvas(self._trade_fig)
        self.trade_canvas.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        right_layout.addWidget(self.trade_canvas, stretch=1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([310, 1000])

        self.statusBar().showMessage("VESPER v0.1 — DEMO")

    def _sep(self):
        sep = QFrame()
        sep.setProperty("class", "separator")
        sep.setFrameShape(QFrame.HLine)
        return sep

    def _build_inputs(self):
        group = QGroupBox("ORBIT PARAMETERS")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)
        layout.setContentsMargins(6, 12, 6, 6)

        self.slider_init = HudSlider(
            label="INITIAL ALTITUDE", min_val=150, max_val=10000,
            value=400, step=10, decimals=0, suffix=" km",
            accent=CYAN,
        )
        layout.addWidget(self.slider_init)

        self.slider_target = HudSlider(
            label="TARGET ALTITUDE", min_val=150, max_val=100000,
            value=35786, step=50, decimals=0, suffix=" km",
            accent=AMBER,
        )
        layout.addWidget(self.slider_target)

        self.slider_inc = HudSlider(
            label="INCLINATION CHANGE", min_val=0.0, max_val=90.0,
            value=0.0, step=0.5, decimals=1, suffix="\u00b0",
            accent=CYAN,
        )
        layout.addWidget(self.slider_inc)

        return group

    def _build_presets(self):
        group = QGroupBox("PRESETS")
        layout = QVBoxLayout(group)
        layout.setSpacing(3)

        presets = [
            ("LEO \u2192 LEO   400 \u2192 800 km", 400, 800, 0.0),
            ("LEO \u2192 MEO   400 \u2192 20200 km", 400, 20200, 0.0),
            ("LEO \u2192 GEO   400 \u2192 35786 km", 400, 35786, 0.0),
            ("LEO \u2192 GEO + 28.5\u00b0 plane \u0394", 400, 35786, 28.5),
            ("ISS \u2192 HEO   420 \u2192 45000 km", 420, 45000, 0.0),
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
            burns_label.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 10px;"
            )
            cl.addWidget(burns_label, 2, 0, 1, 2)

            time_label = QLabel("")
            time_label.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 10px;"
            )
            cl.addWidget(time_label, 3, 0, 1, 2)

            best_label = QLabel("")
            best_label.setProperty("class", "best")
            cl.addWidget(best_label, 4, 0, 1, 2)

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

    # ── Signals ─────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.slider_init.valueChanged.connect(self._schedule_update)
        self.slider_target.valueChanged.connect(self._schedule_update)
        self.slider_inc.valueChanged.connect(self._schedule_update)

    def _schedule_update(self):
        self._update_timer.start()

    # ── Presets ─────────────────────────────────────────────────────────

    def _apply_preset(self, init_alt, target_alt, inc_deg):
        # Block signals to avoid triple-update
        for s in (self.slider_init, self.slider_target, self.slider_inc):
            s.blockSignals(True)

        self.slider_init.setValue(init_alt)
        self.slider_target.setValue(target_alt)
        self.slider_inc.setValue(inc_deg)

        for s in (self.slider_init, self.slider_target, self.slider_inc):
            s.blockSignals(False)

        self._update_all()

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

        # Redraw in-place (no figure recreation, fixed margins)
        update_orbit_figure(self._orbit_ax, alt_init, alt_target, transfers)
        self.orbit_canvas.draw_idle()

        update_trade_figure(self._trade_ax, alt_init, alt_target, delta_inc)
        self.trade_canvas.draw_idle()

        self.statusBar().showMessage(
            f"INIT: {alt_init:.0f} km  \u2502  TARGET: {alt_target:.0f} km"
            f"  \u2502  \u0394i: {delta_inc:.1f}\u00b0  \u2502  "
            f"{len(transfers)} transfer(s)"
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
                w["time"].setText(
                    f"Transfer: {self._fmt_time(t.transfer_time)}"
                )

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

    @staticmethod
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
