"""
VESPER plotting — matplotlib figure generation for orbital visualisations.

Two main figures:
  1. Orbit view — wireframe Earth + glowy orbits + transfer arcs + burn markers
  2. Trade-study — delta-v vs target altitude sweep

Visual style: black background, wireframe/neon aesthetic, layered glow passes.
"""

import numpy as np
import matplotlib
matplotlib.use("QtAgg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyArrowPatch, Polygon
from matplotlib.collections import LineCollection
import matplotlib.ticker as ticker
import matplotlib.patheffects as pe

from vesper.styles import (
    MPL_BG, MPL_FACE, MPL_GRID, MPL_TEXT,
    ORBIT_INITIAL, ORBIT_INITIAL_GLOW, ORBIT_TARGET, ORBIT_TARGET_GLOW,
    ORBIT_TRANSFER, ORBIT_TRANSFER_GLOW, ORBIT_TRANSFER_2,
    BURN_MARKER, EARTH_WIRE, EARTH_WIRE_GLOW, EARTH_FILL,
    CYAN, CYAN_DIM, CYAN_BRIGHT, AMBER, AMBER_BRIGHT,
    AMBER_DIM, TEXT_DIM, GREEN, RED, WHITE, BG_DARKEST,
)
from vesper.mechanics import (
    R_EARTH, alt_to_radius, TransferResult,
    hohmann_transfer, bielliptic_transfer, sweep_target_altitude,
)


# ── Glow helpers ────────────────────────────────────────────────────────────

def _glow_line(ax, x, y, color, linewidth=1.2, alpha=0.9, zorder=3, **kwargs):
    """
    Draw a line with a soft glow effect — three passes of decreasing opacity
    and increasing width underneath the crisp top line.
    """
    # Outer glow (widest, dimmest)
    ax.plot(x, y, color=color, linewidth=linewidth + 4.0, alpha=alpha * 0.06,
            zorder=zorder - 0.3, solid_capstyle="round", **kwargs)
    # Middle glow
    ax.plot(x, y, color=color, linewidth=linewidth + 2.0, alpha=alpha * 0.15,
            zorder=zorder - 0.2, solid_capstyle="round", **kwargs)
    # Inner glow
    ax.plot(x, y, color=color, linewidth=linewidth + 0.8, alpha=alpha * 0.35,
            zorder=zorder - 0.1, solid_capstyle="round", **kwargs)
    # Crisp core
    ax.plot(x, y, color=color, linewidth=linewidth, alpha=alpha,
            zorder=zorder, solid_capstyle="round", **kwargs)


def _glow_circle_patch(ax, radius, color, linewidth=0.6, alpha=0.5, zorder=2,
                        linestyle="-", fill=False, facecolor="none"):
    """Add a circle with a subtle glow ring behind it."""
    # Glow
    ax.add_patch(plt.Circle((0, 0), radius, fill=False,
                              edgecolor=color, linewidth=linewidth + 2.5,
                              alpha=alpha * 0.1, zorder=zorder - 0.1,
                              linestyle=linestyle))
    # Core
    ax.add_patch(plt.Circle((0, 0), radius, fill=fill,
                              facecolor=facecolor,
                              edgecolor=color, linewidth=linewidth,
                              alpha=alpha, zorder=zorder,
                              linestyle=linestyle))


# ── Axes styling ────────────────────────────────────────────────────────────

def _configure_axes(ax, title=None):
    """Apply dark HUD styling to axes."""
    ax.set_facecolor(MPL_BG)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    for side in ("bottom", "left", "top", "right"):
        ax.spines[side].set_color(MPL_GRID)
        ax.spines[side].set_linewidth(0.5)
    if title:
        ax.set_title(title, color=CYAN, fontsize=10, fontweight="bold",
                      fontfamily="monospace", pad=8)


# ── Wireframe Earth ─────────────────────────────────────────────────────────

def _draw_wireframe_earth(ax, r_earth_km):
    """
    Draw Earth as a 2D wireframe sphere — a circle outline plus projected
    latitude and longitude arcs, giving a technical blueprint / HUD look.
    """
    theta = np.linspace(0, 2 * np.pi, 200)

    # Outer rim — glow
    ax.add_patch(plt.Circle((0, 0), r_earth_km, fill=True,
                              facecolor=EARTH_FILL,
                              edgecolor=EARTH_WIRE, linewidth=1.2,
                              alpha=0.9, zorder=5))
    ax.add_patch(plt.Circle((0, 0), r_earth_km, fill=False,
                              edgecolor=EARTH_WIRE, linewidth=3.0,
                              alpha=0.08, zorder=4.9))

    # Longitude lines (meridians) — projected as ellipses seen from front
    n_lon = 8
    for i in range(n_lon):
        angle = i * np.pi / n_lon
        # Each meridian is an ellipse with semi-major = r, semi-minor = r*cos(angle)
        squeeze = np.cos(angle)
        x = r_earth_km * squeeze * np.cos(theta)
        y = r_earth_km * np.sin(theta)
        ax.plot(x, y, color=EARTH_WIRE, linewidth=0.35, alpha=0.40, zorder=5.1)

    # Latitude lines — projected as horizontal lines clipped to circle
    n_lat = 7
    for i in range(1, n_lat):
        lat_frac = -1.0 + 2.0 * i / n_lat  # -1 to 1
        y_pos = lat_frac * r_earth_km
        half_w = np.sqrt(max(0, r_earth_km**2 - y_pos**2))
        if half_w > 0:
            x_lat = np.linspace(-half_w, half_w, 100)
            y_lat = np.full_like(x_lat, y_pos)
            ax.plot(x_lat, y_lat, color=EARTH_WIRE, linewidth=0.30,
                    alpha=0.35, zorder=5.1)

    # Equator — slightly brighter
    x_eq = np.linspace(-r_earth_km, r_earth_km, 100)
    y_eq = np.zeros_like(x_eq)
    ax.plot(x_eq, y_eq, color=EARTH_WIRE, linewidth=0.5, alpha=0.55, zorder=5.2)

    # Centre dot
    ax.plot(0, 0, "o", color=EARTH_WIRE, markersize=2, alpha=0.6, zorder=5.3)


# ── HUD Grid Overlay ───────────────────────────────────────────────────────

def _draw_grid_overlay(ax, max_r_km):
    """Draw subtle concentric range rings, crosshairs, and radial ticks."""
    # Range rings
    for frac in [0.25, 0.5, 0.75, 1.0]:
        r = frac * max_r_km
        _glow_circle_patch(ax, r, MPL_GRID, linewidth=0.3, alpha=0.25,
                            zorder=1, linestyle=(0, (5, 8)))

    # Crosshairs
    ax.axhline(0, color=MPL_GRID, linewidth=0.25, alpha=0.30, zorder=1)
    ax.axvline(0, color=MPL_GRID, linewidth=0.25, alpha=0.30, zorder=1)

    # Diagonal crosshairs (45 degrees)
    d = max_r_km
    ax.plot([-d, d], [-d, d], color=MPL_GRID, linewidth=0.15, alpha=0.15, zorder=1)
    ax.plot([-d, d], [d, -d], color=MPL_GRID, linewidth=0.15, alpha=0.15, zorder=1)


# ── Geometry helpers ────────────────────────────────────────────────────────

def _orbit_xy(radius_m, n=400):
    """Generate x, y coordinates for a circular orbit (in km)."""
    theta = np.linspace(0, 2 * np.pi, n)
    r_km = radius_m / 1000.0
    return r_km * np.cos(theta), r_km * np.sin(theta)


def _transfer_ellipse_xy(a_m, e, start_angle=0.0, sweep=np.pi, n=300):
    """Generate x, y for a transfer ellipse arc (in km)."""
    theta = np.linspace(start_angle, start_angle + sweep, n)
    r = (a_m * (1 - e**2)) / (1 + e * np.cos(theta - start_angle))
    r_km = r / 1000.0
    return r_km * np.cos(theta), r_km * np.sin(theta)


# ── Burn Markers ────────────────────────────────────────────────────────────

def _draw_burn_marker(ax, x, y, label, color, size=7):
    """
    Draw a diamond-shaped burn marker with a halo glow and label.
    """
    # Halo glow
    ax.plot(x, y, marker="D", color=color, markersize=size + 6,
            alpha=0.08, zorder=6.8)
    ax.plot(x, y, marker="D", color=color, markersize=size + 3,
            alpha=0.18, zorder=6.9)
    # Core diamond
    ax.plot(x, y, marker="D", color=color, markersize=size,
            zorder=7, markeredgecolor=WHITE, markeredgewidth=0.6)
    # Inner bright point
    ax.plot(x, y, marker="D", color=WHITE, markersize=size * 0.35,
            alpha=0.7, zorder=7.1)
    # Label
    ax.annotate(label, (x, y), textcoords="offset points",
                 xytext=(10, 10), fontsize=7, color=color,
                 fontweight="bold", fontfamily="monospace",
                 path_effects=[pe.withStroke(linewidth=2, foreground=MPL_BG)])


# ── Main Orbit Figure ──────────────────────────────────────────────────────

def create_orbit_figure(alt_init_km, alt_target_km, transfers, dpi=100):
    """
    Create the main orbit visualisation figure.

    Shows wireframe Earth, initial orbit, target orbit, and transfer orbit(s)
    with glowing lines and diamond burn markers.
    """
    fig = Figure(figsize=(6, 6), dpi=dpi, facecolor=MPL_BG)
    ax = fig.add_subplot(111, aspect="equal")
    _configure_axes(ax, "ORBIT VIEW")

    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)
    r_earth_km = R_EARTH / 1000.0

    # ── Determine plot bounds ──
    max_r = max(r1, r2)
    for t in transfers:
        if t.a_transfer_1 is not None and t.e_transfer_1 is not None:
            r_apo = t.a_transfer_1 * (1 + t.e_transfer_1)
            max_r = max(max_r, r_apo)
        if t.a_transfer_2 is not None and t.e_transfer_2 is not None:
            r_apo = t.a_transfer_2 * (1 + t.e_transfer_2)
            max_r = max(max_r, r_apo)

    max_r_km = max_r / 1000.0 * 1.18
    # Ensure minimum visible size so small-altitude orbits don't get squashed
    max_r_km = max(max_r_km, r_earth_km * 1.6)
    ax.set_xlim(-max_r_km, max_r_km)
    ax.set_ylim(-max_r_km, max_r_km)

    # ── Background grid ──
    _draw_grid_overlay(ax, max_r_km)

    # ── Wireframe Earth ──
    _draw_wireframe_earth(ax, r_earth_km)

    # ── Initial orbit (cyan, glowing) ──
    x1, y1 = _orbit_xy(r1)
    _glow_line(ax, x1, y1, ORBIT_INITIAL, linewidth=1.0, alpha=0.85, zorder=3)
    # Dashed version for "wireframe orbit" feel
    ax.plot(x1[::8], y1[::8], ".", color=ORBIT_INITIAL, markersize=0.5,
            alpha=0.3, zorder=3.1)

    # ── Target orbit (amber, glowing) ──
    x2, y2 = _orbit_xy(r2)
    _glow_line(ax, x2, y2, ORBIT_TARGET, linewidth=1.0, alpha=0.85, zorder=3)

    # ── Transfer arcs ──
    if transfers:
        best = transfers[0]
        _draw_transfer(ax, r1, r2, best, primary=True)

        if len(transfers) >= 2:
            second = transfers[1]
            if second.name != best.name:
                _draw_transfer(ax, r1, r2, second, primary=False)

    # ── Altitude labels on orbits ──
    angle_label = np.radians(55)
    r1_km = r1 / 1000.0
    r2_km = r2 / 1000.0
    ax.annotate(f"{alt_init_km:.0f} km", (r1_km * np.cos(angle_label),
                r1_km * np.sin(angle_label)),
                fontsize=7, color=CYAN_BRIGHT, fontfamily="monospace",
                fontweight="bold", alpha=0.8,
                path_effects=[pe.withStroke(linewidth=2.5, foreground=MPL_BG)])
    ax.annotate(f"{alt_target_km:.0f} km", (r2_km * np.cos(angle_label),
                r2_km * np.sin(angle_label)),
                fontsize=7, color=AMBER_BRIGHT, fontfamily="monospace",
                fontweight="bold", alpha=0.8,
                path_effects=[pe.withStroke(linewidth=2.5, foreground=MPL_BG)])

    # ── Axis formatting ──
    ax.set_xlabel("km", color=TEXT_DIM, fontsize=8, fontfamily="monospace")
    ax.set_ylabel("km", color=TEXT_DIM, fontsize=8, fontfamily="monospace")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{x/1000:.0f}k" if abs(x) >= 1000 else f"{x:.0f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{x/1000:.0f}k" if abs(x) >= 1000 else f"{x:.0f}"))

    # ── Legend ──
    # Custom legend entries since glow_line doesn't return handles easily
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color=ORBIT_INITIAL, linewidth=1.5, label=f"Initial  {alt_init_km:.0f} km"),
        Line2D([0], [0], color=ORBIT_TARGET, linewidth=1.5, label=f"Target  {alt_target_km:.0f} km"),
    ]
    if transfers:
        handles.append(Line2D([0], [0], color=ORBIT_TRANSFER, linewidth=1.2,
                              label=transfers[0].name))
    leg = ax.legend(handles=handles, loc="upper right", fontsize=7,
                     framealpha=0.15, edgecolor=MPL_GRID, facecolor=MPL_BG,
                     labelcolor=TEXT_DIM, borderpad=0.8)
    leg.get_frame().set_linewidth(0.5)

    fig.tight_layout(pad=1.0)
    return fig


def _draw_transfer(ax, r1, r2, transfer: TransferResult, primary=True):
    """Draw a transfer arc with glow and diamond burn markers."""
    alpha = 0.85 if primary else 0.25
    lw = 1.3 if primary else 0.7
    color1 = ORBIT_TRANSFER if primary else ORBIT_TRANSFER_2
    color2 = ORBIT_TRANSFER_2 if primary else ORBIT_TRANSFER

    r1_km = r1 / 1000.0
    r2_km = r2 / 1000.0

    # First transfer ellipse
    if transfer.a_transfer_1 is not None and transfer.e_transfer_1 is not None:
        x, y = _transfer_ellipse_xy(transfer.a_transfer_1, transfer.e_transfer_1)
        if primary:
            _glow_line(ax, x, y, color1, linewidth=lw, alpha=alpha, zorder=4)
        else:
            ax.plot(x, y, color=color1, linewidth=lw, alpha=alpha,
                    linestyle="--", zorder=4)

    # Second transfer ellipse (bi-elliptic)
    if transfer.a_transfer_2 is not None and transfer.e_transfer_2 is not None:
        x, y = _transfer_ellipse_xy(transfer.a_transfer_2, transfer.e_transfer_2,
                                      start_angle=np.pi, sweep=np.pi)
        if primary:
            _glow_line(ax, x, y, color2, linewidth=lw, alpha=alpha * 0.8, zorder=4)
        else:
            ax.plot(x, y, color=color2, linewidth=lw, alpha=alpha,
                    linestyle="--", zorder=4)

    # Burn markers — only on the primary (best) transfer
    if primary:
        # Burn 1: departure at periapsis (right side of initial orbit)
        _draw_burn_marker(ax, r1_km, 0, "B1", BURN_MARKER, size=7)

        if transfer.a_transfer_2 is not None and transfer.e_transfer_1 is not None:
            # Bi-elliptic: B2 at intermediate apoapsis, B3 at target
            r_int_km = transfer.a_transfer_1 * (1 + transfer.e_transfer_1) / 1000.0
            _draw_burn_marker(ax, -r_int_km, 0, "B2", BURN_MARKER, size=7)
            _draw_burn_marker(ax, r2_km, 0, "B3", AMBER, size=6)
        else:
            # Hohmann: B2 at target apoapsis
            _draw_burn_marker(ax, -r2_km, 0, "B2", BURN_MARKER, size=7)


# ── Trade Study Figure ──────────────────────────────────────────────────────

def create_trade_figure(alt_init_km, alt_target_km,
                         delta_inc_deg=0.0, dpi=100):
    """
    Create the trade-study figure: delta-v vs target altitude.
    Glowy lines on black background.
    """
    fig = Figure(figsize=(5.5, 3.0), dpi=dpi, facecolor=MPL_BG)
    ax = fig.add_subplot(111)
    _configure_axes(ax, "TRADE STUDY — \u0394v vs TARGET ALTITUDE")

    # Sweep range
    sweep_max = max(50000, alt_target_km * 1.5)
    altitudes, dv_h, dv_b = sweep_target_altitude(
        alt_init_km, (200, sweep_max), 300, delta_inc_deg
    )

    alt_x = altitudes / 1000.0

    # Hohmann — glowy cyan
    _glow_line(ax, alt_x, dv_h, ORBIT_INITIAL, linewidth=1.2, alpha=0.9, zorder=3)
    # Bi-elliptic — glowy amber dashed
    ax.plot(alt_x, dv_b, color=AMBER, linewidth=2.5, alpha=0.06, zorder=2.7)
    ax.plot(alt_x, dv_b, color=AMBER, linewidth=1.5, alpha=0.15, zorder=2.8)
    ax.plot(alt_x, dv_b, color=AMBER, linewidth=1.0, alpha=0.75,
            linestyle="--", zorder=3, label="Bi-elliptic")

    # Mark current selection
    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)
    h_cur = hohmann_transfer(r1, r2, delta_inc_deg)
    b_cur = bielliptic_transfer(r1, r2, delta_inc_deg=delta_inc_deg)

    # Selection vertical line with glow
    ax.axvline(alt_target_km / 1000.0, color=CYAN_DIM, linewidth=2.0,
               alpha=0.08, zorder=2)
    ax.axvline(alt_target_km / 1000.0, color=CYAN_DIM, linewidth=0.6,
               linestyle=":", alpha=0.5, zorder=2.1)

    # Current point markers with glow
    tx = alt_target_km / 1000.0
    for val, color, ms in [(h_cur.delta_v_total, CYAN, 7),
                            (b_cur.delta_v_total, AMBER, 6)]:
        ax.plot(tx, val, marker="D", color=color, markersize=ms + 4,
                alpha=0.1, zorder=4.8)
        ax.plot(tx, val, marker="D", color=color, markersize=ms,
                zorder=5, markeredgecolor=WHITE, markeredgewidth=0.5)

    ax.set_xlabel("Target Altitude (\u00d71000 km)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.set_ylabel("\u0394v (m/s)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.grid(True, color=MPL_GRID, linewidth=0.3, alpha=0.4)

    # Legend
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color=CYAN, linewidth=1.5, label="Hohmann"),
        Line2D([0], [0], color=AMBER, linewidth=1.2, linestyle="--", label="Bi-elliptic"),
    ]
    leg = ax.legend(handles=handles, loc="upper left", fontsize=7,
                     framealpha=0.15, edgecolor=MPL_GRID, facecolor=MPL_BG,
                     labelcolor=TEXT_DIM, borderpad=0.8)
    leg.get_frame().set_linewidth(0.5)

    fig.tight_layout(pad=1.0)
    return fig
