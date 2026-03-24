"""
VESPER plotting — matplotlib figure generation for orbital visualisations.

Two main figures:
  1. Orbit view — Earth + orbits + transfer arcs + burn markers
  2. Trade-study — delta-v vs target altitude sweep
"""

import numpy as np
import matplotlib
matplotlib.use("QtAgg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyArrowPatch
from matplotlib.collections import LineCollection
import matplotlib.ticker as ticker

from vesper.styles import (
    MPL_BG, MPL_FACE, MPL_GRID, MPL_TEXT,
    ORBIT_INITIAL, ORBIT_TARGET, ORBIT_TRANSFER, ORBIT_TRANSFER_2,
    BURN_MARKER, EARTH_COLOR, EARTH_EDGE, CYAN, CYAN_DIM, AMBER,
    AMBER_DIM, TEXT_DIM, GREEN, RED, WHITE, BG_DARKEST,
)
from vesper.mechanics import (
    R_EARTH, alt_to_radius, TransferResult,
    hohmann_transfer, bielliptic_transfer, sweep_target_altitude,
)


def _configure_axes(ax, title=None):
    """Apply dark HUD styling to axes."""
    ax.set_facecolor(MPL_BG)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    ax.spines["bottom"].set_color(MPL_GRID)
    ax.spines["left"].set_color(MPL_GRID)
    ax.spines["top"].set_color(MPL_GRID)
    ax.spines["right"].set_color(MPL_GRID)
    for spine in ax.spines.values():
        spine.set_linewidth(0.5)
    if title:
        ax.set_title(title, color=CYAN, fontsize=10, fontweight="bold",
                      fontfamily="monospace", pad=8)


def _draw_grid_overlay(ax, max_r_km):
    """Draw subtle concentric range rings and crosshairs."""
    for frac in [0.25, 0.5, 0.75, 1.0]:
        r = frac * max_r_km
        circle = plt.Circle((0, 0), r, fill=False,
                              edgecolor=MPL_GRID, linewidth=0.3,
                              linestyle="--", alpha=0.4)
        ax.add_patch(circle)
    # Crosshairs
    ax.axhline(0, color=MPL_GRID, linewidth=0.3, alpha=0.4)
    ax.axvline(0, color=MPL_GRID, linewidth=0.3, alpha=0.4)


def _orbit_xy(radius_m, n=360):
    """Generate x, y coordinates for a circular orbit (in km)."""
    theta = np.linspace(0, 2 * np.pi, n)
    r_km = radius_m / 1000.0
    return r_km * np.cos(theta), r_km * np.sin(theta)


def _transfer_ellipse_xy(a_m, e, start_angle=0.0, sweep=np.pi, n=200):
    """Generate x, y for a transfer ellipse arc (in km)."""
    theta = np.linspace(start_angle, start_angle + sweep, n)
    r = (a_m * (1 - e**2)) / (1 + e * np.cos(theta - start_angle))
    r_km = r / 1000.0
    return r_km * np.cos(theta), r_km * np.sin(theta)


def create_orbit_figure(alt_init_km, alt_target_km, transfers, dpi=100):
    """
    Create the main orbit visualisation figure.

    Shows Earth, initial orbit, target orbit, and transfer orbit(s)
    with burn markers.
    """
    fig = Figure(figsize=(6, 6), dpi=dpi, facecolor=MPL_BG)
    ax = fig.add_subplot(111, aspect="equal")
    _configure_axes(ax, "ORBIT VIEW")

    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)
    r_earth_km = R_EARTH / 1000.0

    # Determine plot bounds
    max_r = max(r1, r2)
    # Check if any transfer has a larger intermediate orbit
    for t in transfers:
        if t.a_transfer_1 and t.e_transfer_1:
            r_apo = t.a_transfer_1 * (1 + t.e_transfer_1) / 1000.0
            max_r = max(max_r, r_apo * 1000.0)
        if t.a_transfer_2 and t.e_transfer_2:
            r_apo = t.a_transfer_2 * (1 + t.e_transfer_2) / 1000.0
            max_r = max(max_r, r_apo * 1000.0)

    max_r_km = max_r / 1000.0 * 1.15
    ax.set_xlim(-max_r_km, max_r_km)
    ax.set_ylim(-max_r_km, max_r_km)

    # Grid overlay
    _draw_grid_overlay(ax, max_r_km)

    # Earth
    earth = plt.Circle((0, 0), r_earth_km, color=EARTH_COLOR,
                         ec=EARTH_EDGE, linewidth=0.8, alpha=0.85, zorder=5)
    ax.add_patch(earth)
    ax.text(0, 0, "E", ha="center", va="center",
            color=WHITE, fontsize=8, fontweight="bold",
            fontfamily="monospace", zorder=6, alpha=0.7)

    # Initial orbit
    x1, y1 = _orbit_xy(r1)
    ax.plot(x1, y1, color=ORBIT_INITIAL, linewidth=1.2, alpha=0.9,
            label=f"Initial  {alt_init_km:.0f} km", zorder=3)

    # Target orbit
    x2, y2 = _orbit_xy(r2)
    ax.plot(x2, y2, color=ORBIT_TARGET, linewidth=1.2, alpha=0.9,
            label=f"Target  {alt_target_km:.0f} km", zorder=3)

    # Draw the best (first) transfer — keep it simple for the demo
    if transfers:
        best = transfers[0]
        _draw_transfer(ax, r1, r2, best, primary=True)

        # If there's a second transfer type, draw it dimmer
        if len(transfers) >= 2:
            second = transfers[1]
            if second.name != best.name:
                _draw_transfer(ax, r1, r2, second, primary=False)

    # Axis labels
    ax.set_xlabel("km", color=TEXT_DIM, fontsize=8, fontfamily="monospace")
    ax.set_ylabel("km", color=TEXT_DIM, fontsize=8, fontfamily="monospace")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{x/1000:.0f}k" if abs(x) >= 1000 else f"{x:.0f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{x/1000:.0f}k" if abs(x) >= 1000 else f"{x:.0f}"))

    # Legend
    leg = ax.legend(loc="upper right", fontsize=7, framealpha=0.3,
                     edgecolor=MPL_GRID, facecolor=MPL_BG,
                     labelcolor=TEXT_DIM, borderpad=0.8)
    leg.get_frame().set_linewidth(0.5)

    fig.tight_layout(pad=1.0)
    return fig


def _draw_transfer(ax, r1, r2, transfer: TransferResult, primary=True):
    """Draw a transfer arc with burn markers."""
    alpha = 0.9 if primary else 0.35
    lw = 1.5 if primary else 0.8
    color1 = ORBIT_TRANSFER if primary else ORBIT_TRANSFER_2
    color2 = ORBIT_TRANSFER_2 if primary else ORBIT_TRANSFER

    r1_km = r1 / 1000.0
    r2_km = r2 / 1000.0

    # First transfer ellipse
    if transfer.a_transfer_1 and transfer.e_transfer_1 is not None:
        x, y = _transfer_ellipse_xy(transfer.a_transfer_1, transfer.e_transfer_1)
        ax.plot(x, y, color=color1, linewidth=lw, alpha=alpha,
                linestyle="-", zorder=4,
                label=transfer.name if primary else f"_{transfer.name}")

    # Second transfer ellipse (bi-elliptic)
    if transfer.a_transfer_2 is not None and transfer.e_transfer_2 is not None:
        x, y = _transfer_ellipse_xy(transfer.a_transfer_2, transfer.e_transfer_2,
                                      start_angle=np.pi, sweep=np.pi)
        ax.plot(x, y, color=color2, linewidth=lw, alpha=alpha,
                linestyle="--", zorder=4)

    # Burn markers
    if primary:
        # Burn 1 at periapsis (right side of initial orbit)
        ax.plot(r1_km, 0, marker="^", color=BURN_MARKER, markersize=8,
                zorder=7, markeredgecolor=WHITE, markeredgewidth=0.5)
        ax.annotate("B1", (r1_km, 0), textcoords="offset points",
                     xytext=(8, 8), fontsize=7, color=BURN_MARKER,
                     fontweight="bold", fontfamily="monospace")

        # Burn 2 at apoapsis (left side)
        if transfer.a_transfer_2 is not None:
            # Bi-elliptic: burn 2 at intermediate, burn 3 at target
            r_int = transfer.a_transfer_1 * (1 + transfer.e_transfer_1) / 1000.0
            ax.plot(-r_int, 0, marker="^", color=BURN_MARKER, markersize=8,
                    zorder=7, markeredgecolor=WHITE, markeredgewidth=0.5)
            ax.annotate("B2", (-r_int, 0), textcoords="offset points",
                         xytext=(-16, 8), fontsize=7, color=BURN_MARKER,
                         fontweight="bold", fontfamily="monospace")
            ax.plot(r2_km, 0, marker="^", color=AMBER, markersize=7,
                    zorder=7, markeredgecolor=WHITE, markeredgewidth=0.5)
            ax.annotate("B3", (r2_km, 0), textcoords="offset points",
                         xytext=(8, -12), fontsize=7, color=AMBER,
                         fontweight="bold", fontfamily="monospace")
        else:
            ax.plot(-r2_km, 0, marker="^", color=BURN_MARKER, markersize=8,
                    zorder=7, markeredgecolor=WHITE, markeredgewidth=0.5)
            ax.annotate("B2", (-r2_km, 0), textcoords="offset points",
                         xytext=(-16, 8), fontsize=7, color=BURN_MARKER,
                         fontweight="bold", fontfamily="monospace")


def create_trade_figure(alt_init_km, alt_target_km,
                         delta_inc_deg=0.0, dpi=100):
    """
    Create the trade-study figure: delta-v vs target altitude.
    """
    fig = Figure(figsize=(5.5, 3.0), dpi=dpi, facecolor=MPL_BG)
    ax = fig.add_subplot(111)
    _configure_axes(ax, "TRADE STUDY — \u0394v vs TARGET ALTITUDE")

    # Sweep range: from 200 km to max(50000, target*1.5)
    sweep_max = max(50000, alt_target_km * 1.5)
    altitudes, dv_h, dv_b = sweep_target_altitude(
        alt_init_km, (200, sweep_max), 300, delta_inc_deg
    )

    ax.plot(altitudes / 1000.0, dv_h, color=ORBIT_INITIAL, linewidth=1.2,
            alpha=0.9, label="Hohmann")
    ax.plot(altitudes / 1000.0, dv_b, color=AMBER, linewidth=1.0,
            alpha=0.75, linestyle="--", label="Bi-elliptic")

    # Mark current selection
    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)
    h_cur = hohmann_transfer(r1, r2, delta_inc_deg)
    b_cur = bielliptic_transfer(r1, r2, delta_inc_deg=delta_inc_deg)

    ax.axvline(alt_target_km / 1000.0, color=CYAN_DIM, linewidth=0.6,
               linestyle=":", alpha=0.6)
    ax.plot(alt_target_km / 1000.0, h_cur.delta_v_total,
            marker="o", color=CYAN, markersize=6, zorder=5,
            markeredgecolor=WHITE, markeredgewidth=0.5)
    ax.plot(alt_target_km / 1000.0, b_cur.delta_v_total,
            marker="s", color=AMBER, markersize=5, zorder=5,
            markeredgecolor=WHITE, markeredgewidth=0.5)

    ax.set_xlabel("Target Altitude (×1000 km)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.set_ylabel("\u0394v (m/s)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.grid(True, color=MPL_GRID, linewidth=0.3, alpha=0.5)

    leg = ax.legend(loc="upper left", fontsize=7, framealpha=0.3,
                     edgecolor=MPL_GRID, facecolor=MPL_BG,
                     labelcolor=TEXT_DIM, borderpad=0.8)
    leg.get_frame().set_linewidth(0.5)

    fig.tight_layout(pad=1.0)
    return fig
