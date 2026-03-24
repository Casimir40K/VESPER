"""
VESPER plotting — matplotlib figure generation for orbital visualisations.

Performance: figures created once, axes cleared and redrawn in-place.
Visual style: black bg, Evangelion-inspired neon lines with faint glow bloom.

Provides:
  - Orbit view (wireframe Earth + glowing orbits + transfer arcs + burns)
  - Trade study: dv vs altitude
  - Trade study: dv vs inclination change
  - Trade study: transfer time vs altitude
  - Plane change comparison bar chart
"""

import numpy as np
import matplotlib
matplotlib.use("QtAgg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import matplotlib.ticker as ticker
import matplotlib.patheffects as pe

from vesper.styles import (
    MPL_BG, MPL_GRID,
    ORBIT_INITIAL, ORBIT_INITIAL_GLOW, ORBIT_TARGET, ORBIT_TARGET_GLOW,
    ORBIT_TRANSFER, ORBIT_TRANSFER_2,
    BURN_MARKER, EARTH_WIRE, EARTH_FILL,
    CYAN, CYAN_DIM, CYAN_BRIGHT, CYAN_GLOW,
    AMBER, AMBER_BRIGHT, AMBER_GLOW, AMBER_DIM,
    RED, RED_GLOW, GREEN,
    TEXT_DIM, TEXT_LABEL, TEXT_PRIMARY, WHITE,
)
from vesper.mechanics import (
    R_EARTH, alt_to_radius, TransferResult, orbital_velocity,
    hohmann_transfer, bielliptic_transfer, sweep_target_altitude,
)

# Precomputed angle arrays
_THETA_200 = np.linspace(0, 2 * np.pi, 200)
_COS_200 = np.cos(_THETA_200)
_SIN_200 = np.sin(_THETA_200)


# ── Glow helpers ────────────────────────────────────────────────────────────

def _glow_line(ax, x, y, color, lw=1.2, alpha=0.9, zorder=3):
    """
    Draw a line with 4-layer glow bloom.
    Outermost layer is very wide and faint for the soft bloom effect.
    """
    # Wide bloom (faintest, widest)
    ax.plot(x, y, color=color, lw=lw + 8.0, alpha=alpha * 0.025,
            zorder=zorder - 0.4, solid_capstyle="round")
    # Outer glow
    ax.plot(x, y, color=color, lw=lw + 4.0, alpha=alpha * 0.06,
            zorder=zorder - 0.3, solid_capstyle="round")
    # Inner glow
    ax.plot(x, y, color=color, lw=lw + 1.8, alpha=alpha * 0.18,
            zorder=zorder - 0.2, solid_capstyle="round")
    # Crisp core
    ax.plot(x, y, color=color, lw=lw, alpha=alpha,
            zorder=zorder, solid_capstyle="round")


def _glow_circle(ax, radius, color, lw=0.3, alpha=0.25, zorder=1,
                 ls=(0, (5, 8))):
    ax.add_patch(plt.Circle((0, 0), radius, fill=False, ec=color,
                              lw=lw + 2.0, alpha=alpha * 0.1,
                              zorder=zorder - 0.1, ls=ls))
    ax.add_patch(plt.Circle((0, 0), radius, fill=False, ec=color,
                              lw=lw, alpha=alpha, zorder=zorder, ls=ls))


# ── Axes styling ────────────────────────────────────────────────────────────

def _configure_axes(ax, title=None):
    ax.set_facecolor(MPL_BG)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    for s in ax.spines.values():
        s.set_color(MPL_GRID)
        s.set_linewidth(0.5)
    if title:
        ax.set_title(title, color=AMBER, fontsize=10, fontweight="bold",
                      fontfamily="monospace", pad=8)


# ── Wireframe Earth ─────────────────────────────────────────────────────────

def _draw_wireframe_earth(ax, r):
    # Filled disc + rim
    ax.add_patch(plt.Circle((0, 0), r, fc=EARTH_FILL, ec=EARTH_WIRE,
                              lw=1.2, alpha=0.9, zorder=5))
    # Rim glow
    ax.add_patch(plt.Circle((0, 0), r, fill=False, ec=EARTH_WIRE,
                              lw=4.0, alpha=0.06, zorder=4.8))
    ax.add_patch(plt.Circle((0, 0), r, fill=False, ec=EARTH_WIRE,
                              lw=3.0, alpha=0.08, zorder=4.9))

    # Meridians
    for i in range(8):
        sq = np.cos(i * np.pi / 8)
        ax.plot(r * sq * _COS_200, r * _SIN_200,
                color=EARTH_WIRE, lw=0.35, alpha=0.40, zorder=5.1)

    # Latitudes
    for i in range(1, 7):
        f = -1.0 + 2.0 * i / 7
        yp = f * r
        hw = np.sqrt(max(0, r * r - yp * yp))
        if hw > 0:
            xl = np.linspace(-hw, hw, 60)
            ax.plot(xl, np.full_like(xl, yp),
                    color=EARTH_WIRE, lw=0.30, alpha=0.35, zorder=5.1)

    # Equator
    ax.plot([-r, r], [0, 0], color=EARTH_WIRE, lw=0.5, alpha=0.55, zorder=5.2)
    ax.plot(0, 0, "o", color=EARTH_WIRE, ms=2, alpha=0.6, zorder=5.3)


# ── HUD Grid ───────────────────────────────────────────────────────────────

def _draw_grid(ax, max_r):
    for frac in (0.25, 0.5, 0.75, 1.0):
        _glow_circle(ax, frac * max_r, MPL_GRID)
    ax.axhline(0, color=MPL_GRID, lw=0.25, alpha=0.30, zorder=1)
    ax.axvline(0, color=MPL_GRID, lw=0.25, alpha=0.30, zorder=1)
    d = max_r
    ax.plot([-d, d], [-d, d], color=MPL_GRID, lw=0.15, alpha=0.15, zorder=1)
    ax.plot([-d, d], [d, -d], color=MPL_GRID, lw=0.15, alpha=0.15, zorder=1)


# ── Geometry ────────────────────────────────────────────────────────────────

def _orbit_xy(radius_m):
    r = radius_m / 1000.0
    return r * _COS_200, r * _SIN_200


def _transfer_xy(a_m, e, start=0.0, sweep=np.pi, n=180):
    theta = np.linspace(start, start + sweep, n)
    r = (a_m * (1 - e**2)) / (1 + e * np.cos(theta - start)) / 1000.0
    return r * np.cos(theta), r * np.sin(theta)


# ── Burn Markers ────────────────────────────────────────────────────────────

_STROKE = [pe.withStroke(linewidth=2.5, foreground=MPL_BG)]

def _burn_marker(ax, x, y, label, color, sz=7):
    # Bloom halo
    ax.plot(x, y, "D", color=color, ms=sz + 8, alpha=0.04, zorder=6.7)
    ax.plot(x, y, "D", color=color, ms=sz + 5, alpha=0.08, zorder=6.8)
    ax.plot(x, y, "D", color=color, ms=sz + 2, alpha=0.18, zorder=6.9)
    # Core
    ax.plot(x, y, "D", color=color, ms=sz, zorder=7, mec=WHITE, mew=0.6)
    ax.plot(x, y, "D", color=WHITE, ms=sz * 0.35, alpha=0.7, zorder=7.1)
    # Label
    ax.annotate(label, (x, y), textcoords="offset points", xytext=(10, 10),
                fontsize=7, color=color, fontweight="bold",
                fontfamily="monospace", path_effects=_STROKE)


def _velocity_arrow(ax, x, y, angle_deg, length, color, label=""):
    """Draw a small velocity-change arrow at a burn point."""
    rad = np.radians(angle_deg)
    dx, dy = length * np.cos(rad), length * np.sin(rad)
    ax.annotate("", xy=(x + dx, y + dy), xytext=(x, y),
                arrowprops=dict(arrowstyle="->", color=color,
                                lw=1.2, shrinkA=0, shrinkB=0),
                zorder=8)
    if label:
        ax.annotate(label, (x + dx * 0.5, y + dy * 0.5),
                    fontsize=6, color=color, fontfamily="monospace",
                    alpha=0.8, path_effects=_STROKE)


# ── Figure Factories (called once) ─────────────────────────────────────────

def create_orbit_figure(dpi=100):
    fig = Figure(figsize=(6, 6), dpi=dpi, facecolor=MPL_BG)
    ax = fig.add_subplot(111, aspect="equal")
    fig.subplots_adjust(left=0.12, right=0.95, top=0.93, bottom=0.08)
    return fig, ax


def create_trade_figure(dpi=100, left_margin=0.12):
    fig = Figure(figsize=(5.5, 3.0), dpi=dpi, facecolor=MPL_BG)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=left_margin, right=0.96, top=0.88, bottom=0.18)
    return fig, ax


# ── In-place Update: Orbit View ────────────────────────────────────────────

def update_orbit_figure(ax, alt_init_km, alt_target_km, transfers):
    ax.cla()
    _configure_axes(ax, "ORBIT VIEW")

    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)
    re_km = R_EARTH / 1000.0

    # Bounds
    max_r = max(r1, r2)
    for t in transfers:
        if t.a_transfer_1 is not None and t.e_transfer_1 is not None:
            max_r = max(max_r, t.a_transfer_1 * (1 + t.e_transfer_1))
        if t.a_transfer_2 is not None and t.e_transfer_2 is not None:
            max_r = max(max_r, t.a_transfer_2 * (1 + t.e_transfer_2))
    mr = max(max_r / 1000.0 * 1.18, re_km * 1.6)
    ax.set_xlim(-mr, mr)
    ax.set_ylim(-mr, mr)

    _draw_grid(ax, mr)
    _draw_wireframe_earth(ax, re_km)

    # Initial orbit (cyan, glowing)
    x1, y1 = _orbit_xy(r1)
    _glow_line(ax, x1, y1, ORBIT_INITIAL, lw=1.0, alpha=0.85, zorder=3)

    # Target orbit (amber, glowing)
    x2, y2 = _orbit_xy(r2)
    _glow_line(ax, x2, y2, ORBIT_TARGET, lw=1.0, alpha=0.85, zorder=3)

    # Transfer arcs
    if transfers:
        _draw_xfer(ax, r1, r2, transfers[0], True)
        if len(transfers) >= 2 and transfers[1].name != transfers[0].name:
            _draw_xfer(ax, r1, r2, transfers[1], False)

    # ── Altitude labels with connectors ──
    ang = np.radians(55)
    ca, sa = np.cos(ang), np.sin(ang)
    for alt, r, col in [(alt_init_km, r1, CYAN_BRIGHT),
                         (alt_target_km, r2, AMBER_BRIGHT)]:
        rk = r / 1000.0
        px, py = rk * ca, rk * sa
        ax.annotate(
            f"{alt:.0f} km",
            (px, py),
            fontsize=7, color=col, fontfamily="monospace",
            fontweight="bold", alpha=0.9,
            path_effects=[pe.withStroke(linewidth=3, foreground=MPL_BG)],
        )

    # ── Periapsis / Apoapsis labels for transfer ──
    if transfers:
        best = transfers[0]
        r1k, r2k = r1 / 1000.0, r2 / 1000.0
        # Periapsis label
        ax.annotate("Pe", (r1k + mr * 0.02, -mr * 0.04),
                    fontsize=6, color=TEXT_DIM, fontfamily="monospace",
                    alpha=0.6, path_effects=_STROKE)
        if best.a_transfer_2 is not None and best.e_transfer_1 is not None:
            ra_km = best.a_transfer_1 * (1 + best.e_transfer_1) / 1000.0
            ax.annotate("Ap", (-ra_km - mr * 0.06, -mr * 0.04),
                        fontsize=6, color=TEXT_DIM, fontfamily="monospace",
                        alpha=0.6, path_effects=_STROKE)
        else:
            ax.annotate("Ap", (-r2k - mr * 0.06, -mr * 0.04),
                        fontsize=6, color=TEXT_DIM, fontfamily="monospace",
                        alpha=0.6, path_effects=_STROKE)

    # Axes formatting
    ax.set_xlabel("km", color=TEXT_DIM, fontsize=8, fontfamily="monospace")
    ax.set_ylabel("km", color=TEXT_DIM, fontsize=8, fontfamily="monospace")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{x/1000:.0f}k" if abs(x) >= 1000 else f"{x:.0f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{x/1000:.0f}k" if abs(x) >= 1000 else f"{x:.0f}"))

    # Legend
    handles = [
        Line2D([0], [0], color=ORBIT_INITIAL, lw=1.5,
               label=f"Initial  {alt_init_km:.0f} km"),
        Line2D([0], [0], color=ORBIT_TARGET, lw=1.5,
               label=f"Target  {alt_target_km:.0f} km"),
    ]
    if transfers:
        handles.append(Line2D([0], [0], color=ORBIT_TRANSFER, lw=1.2,
                              label=transfers[0].name))
    leg = ax.legend(handles=handles, loc="upper right", fontsize=7,
                     framealpha=0.15, edgecolor=MPL_GRID, facecolor=MPL_BG,
                     labelcolor=TEXT_DIM, borderpad=0.8)
    leg.get_frame().set_linewidth(0.5)


def _draw_xfer(ax, r1, r2, t, primary):
    a = 0.85 if primary else 0.25
    lw = 1.3 if primary else 0.7
    c1 = ORBIT_TRANSFER if primary else ORBIT_TRANSFER_2
    c2 = ORBIT_TRANSFER_2 if primary else ORBIT_TRANSFER

    if t.a_transfer_1 is not None and t.e_transfer_1 is not None:
        x, y = _transfer_xy(t.a_transfer_1, t.e_transfer_1)
        if primary:
            _glow_line(ax, x, y, c1, lw=lw, alpha=a, zorder=4)
        else:
            ax.plot(x, y, color=c1, lw=lw, alpha=a, ls="--", zorder=4)

    if t.a_transfer_2 is not None and t.e_transfer_2 is not None:
        x, y = _transfer_xy(t.a_transfer_2, t.e_transfer_2,
                              start=np.pi, sweep=np.pi)
        if primary:
            _glow_line(ax, x, y, c2, lw=lw, alpha=a * 0.8, zorder=4)
        else:
            ax.plot(x, y, color=c2, lw=lw, alpha=a, ls="--", zorder=4)

    if primary:
        r1k, r2k = r1 / 1000.0, r2 / 1000.0
        _burn_marker(ax, r1k, 0, "B1", BURN_MARKER)

        # Velocity arrows at burn points
        arrow_len = max(r1k, r2k) * 0.06
        _velocity_arrow(ax, r1k, 0, 90, arrow_len, BURN_MARKER, "\u0394v\u2081")

        if t.a_transfer_2 is not None and t.e_transfer_1 is not None:
            ri = t.a_transfer_1 * (1 + t.e_transfer_1) / 1000.0
            _burn_marker(ax, -ri, 0, "B2", BURN_MARKER)
            _burn_marker(ax, r2k, 0, "B3", AMBER, sz=6)
            _velocity_arrow(ax, -ri, 0, -90, arrow_len, BURN_MARKER)
        else:
            _burn_marker(ax, -r2k, 0, "B2", BURN_MARKER)
            _velocity_arrow(ax, -r2k, 0, -90, arrow_len, BURN_MARKER, "\u0394v\u2082")


# ── In-place Update: Trade Study (dv vs altitude) ──────────────────────────

def update_trade_figure(ax, alt_init_km, alt_target_km, delta_inc_deg=0.0):
    ax.cla()
    _configure_axes(ax, "\u0394v  vs  TARGET ALTITUDE")

    sweep_max = max(50000, alt_target_km * 1.5)
    alts, dv_h, dv_b = sweep_target_altitude(
        alt_init_km, (200, sweep_max), 200, delta_inc_deg
    )
    ax_km = alts / 1000.0

    # Hohmann — cyan glow
    _glow_line(ax, ax_km, dv_h, ORBIT_INITIAL, lw=1.2, alpha=0.9, zorder=3)
    # Bi-elliptic — amber glow + dashed
    ax.plot(ax_km, dv_b, color=AMBER, lw=6.0, alpha=0.02, zorder=2.6)
    ax.plot(ax_km, dv_b, color=AMBER, lw=3.0, alpha=0.06, zorder=2.7)
    ax.plot(ax_km, dv_b, color=AMBER, lw=1.0, alpha=0.75, ls="--", zorder=3)

    # Current selection marker
    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)
    h = hohmann_transfer(r1, r2, delta_inc_deg)
    b = bielliptic_transfer(r1, r2, delta_inc_deg=delta_inc_deg)
    tx = alt_target_km / 1000.0

    ax.axvline(tx, color=AMBER_DIM, lw=2.0, alpha=0.08, zorder=2)
    ax.axvline(tx, color=AMBER_DIM, lw=0.6, ls=":", alpha=0.5, zorder=2.1)

    for val, col, ms in [(h.delta_v_total, CYAN, 7),
                          (b.delta_v_total, AMBER, 6)]:
        ax.plot(tx, val, "D", color=col, ms=ms + 6, alpha=0.04, zorder=4.7)
        ax.plot(tx, val, "D", color=col, ms=ms + 4, alpha=0.1, zorder=4.8)
        ax.plot(tx, val, "D", color=col, ms=ms, zorder=5, mec=WHITE, mew=0.5)

    ax.set_xlabel("Target Altitude (\u00d71000 km)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.set_ylabel("\u0394v (m/s)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.grid(True, color=MPL_GRID, lw=0.3, alpha=0.4)

    handles = [
        Line2D([0], [0], color=CYAN, lw=1.5, label="Hohmann"),
        Line2D([0], [0], color=AMBER, lw=1.2, ls="--", label="Bi-elliptic"),
    ]
    leg = ax.legend(handles=handles, loc="upper left", fontsize=7,
                     framealpha=0.15, edgecolor=MPL_GRID, facecolor=MPL_BG,
                     labelcolor=TEXT_DIM, borderpad=0.8)
    leg.get_frame().set_linewidth(0.5)


# ── Trade Study: dv vs inclination ─────────────────────────────────────────

def update_trade_inclination(ax, alt_init_km, alt_target_km):
    """Plot dv vs inclination change (0-60 deg)."""
    ax.cla()
    _configure_axes(ax, "\u0394v  vs  INCLINATION CHANGE")

    from vesper.mechanics import sweep_inclination
    incs, dv_h, dv_b = sweep_inclination(alt_init_km, alt_target_km,
                                          inc_range=(0, 60), n_points=120)

    _glow_line(ax, incs, dv_h, CYAN, lw=1.2, alpha=0.9, zorder=3)
    ax.plot(incs, dv_b, color=AMBER, lw=6.0, alpha=0.02, zorder=2.6)
    ax.plot(incs, dv_b, color=AMBER, lw=3.0, alpha=0.06, zorder=2.7)
    ax.plot(incs, dv_b, color=AMBER, lw=1.0, alpha=0.75, ls="--", zorder=3)

    # Reference: pure plane change cost at initial orbit
    r1 = alt_to_radius(alt_init_km)
    v1 = orbital_velocity(r1)
    incs_rad = np.radians(incs)
    dv_pure = 2 * v1 * np.sin(incs_rad / 2)
    ax.plot(incs, dv_pure, color=RED, lw=0.8, alpha=0.5, ls=":", zorder=2.5)

    ax.set_xlabel("Inclination Change (\u00b0)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.set_ylabel("\u0394v (m/s)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.grid(True, color=MPL_GRID, lw=0.3, alpha=0.4)

    handles = [
        Line2D([0], [0], color=CYAN, lw=1.5, label="Hohmann + plane \u0394"),
        Line2D([0], [0], color=AMBER, lw=1.2, ls="--",
               label="Bi-elliptic + plane \u0394"),
        Line2D([0], [0], color=RED, lw=0.8, ls=":",
               label="Pure plane change (LEO)"),
    ]
    leg = ax.legend(handles=handles, loc="upper left", fontsize=7,
                     framealpha=0.15, edgecolor=MPL_GRID, facecolor=MPL_BG,
                     labelcolor=TEXT_DIM, borderpad=0.8)
    leg.get_frame().set_linewidth(0.5)


# ── Trade Study: transfer time vs altitude ──────────────────────────────────

def update_trade_time(ax, alt_init_km, alt_target_km):
    """Plot transfer time vs target altitude."""
    ax.cla()
    _configure_axes(ax, "TRANSFER TIME  vs  TARGET ALTITUDE")

    from vesper.mechanics import sweep_transfer_time
    alts, th, tb = sweep_transfer_time(alt_init_km,
                                        alt_range_km=(200, max(50000, alt_target_km * 1.5)),
                                        n_points=150)
    ax_km = alts / 1000.0

    _glow_line(ax, ax_km, th, CYAN, lw=1.2, alpha=0.9, zorder=3)
    ax.plot(ax_km, tb, color=AMBER, lw=6.0, alpha=0.02, zorder=2.6)
    ax.plot(ax_km, tb, color=AMBER, lw=3.0, alpha=0.06, zorder=2.7)
    ax.plot(ax_km, tb, color=AMBER, lw=1.0, alpha=0.75, ls="--", zorder=3)

    # Mark current target
    tx = alt_target_km / 1000.0
    ax.axvline(tx, color=AMBER_DIM, lw=0.6, ls=":", alpha=0.5, zorder=2.1)

    ax.set_xlabel("Target Altitude (\u00d71000 km)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.set_ylabel("Transfer Time (hours)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.grid(True, color=MPL_GRID, lw=0.3, alpha=0.4)

    handles = [
        Line2D([0], [0], color=CYAN, lw=1.5, label="Hohmann"),
        Line2D([0], [0], color=AMBER, lw=1.2, ls="--", label="Bi-elliptic"),
    ]
    leg = ax.legend(handles=handles, loc="upper left", fontsize=7,
                     framealpha=0.15, edgecolor=MPL_GRID, facecolor=MPL_BG,
                     labelcolor=TEXT_DIM, borderpad=0.8)
    leg.get_frame().set_linewidth(0.5)


# ── Plane Change Comparison Bar Chart ──────────────────────────────────────

def update_plane_change_chart(ax, strategies):
    """
    Draw a horizontal bar chart comparing plane change strategies.
    strategies: list of PlaneChangeStrategy from mechanics.
    """
    ax.cla()
    _configure_axes(ax, "PLANE CHANGE STRATEGY COMPARISON")

    if not strategies:
        ax.text(0.5, 0.5, "Set inclination > 0\u00b0",
                ha="center", va="center", color=TEXT_DIM,
                fontfamily="monospace", fontsize=10,
                transform=ax.transAxes)
        return

    n = len(strategies)
    y_pos = np.arange(n)
    dvs = [s.delta_v_total for s in strategies]
    best_dv = min(dvs)

    colors = []
    for dv in dvs:
        if abs(dv - best_dv) < 0.1:
            colors.append(AMBER_BRIGHT)
        else:
            colors.append(CYAN_DIM)

    bars = ax.barh(y_pos, dvs, height=0.6, color=colors, edgecolor=AMBER_DIM,
                    linewidth=0.5, zorder=3)

    # Glow behind bars
    for i, (bar, dv) in enumerate(zip(bars, dvs)):
        if abs(dv - best_dv) < 0.1:
            ax.barh(y_pos[i], dv, height=0.8, color=AMBER,
                    alpha=0.06, zorder=2)

    ax.set_yticks(y_pos)
    ax.set_yticklabels([s.name for s in strategies],
                        fontsize=7, fontfamily="monospace", color=TEXT_PRIMARY)
    ax.set_xlabel("\u0394v total (m/s)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.invert_yaxis()
    ax.grid(True, axis="x", color=MPL_GRID, lw=0.3, alpha=0.4)

    # Value labels on bars
    for i, (bar, dv) in enumerate(zip(bars, dvs)):
        label = f"{dv:.0f} m/s"
        if abs(dv - best_dv) < 0.1:
            label += "  \u2713 BEST"
        ax.text(dv + max(dvs) * 0.02, i, label,
                va="center", fontsize=7, color=TEXT_PRIMARY,
                fontfamily="monospace",
                path_effects=[pe.withStroke(linewidth=2, foreground=MPL_BG)])


# ── Mission Chain Diagram ───────────────────────────────────────────────────

def update_mission_chain_figure(ax, legs, total_dv, total_time):
    """Draw a mission chain summary diagram."""
    ax.cla()
    _configure_axes(ax, "MISSION CHAIN")

    if not legs:
        ax.text(0.5, 0.5, "No mission legs defined",
                ha="center", va="center", color=TEXT_DIM,
                fontfamily="monospace", fontsize=10,
                transform=ax.transAxes)
        return

    n = len(legs)
    x_pos = np.arange(n)
    dvs = [leg.result.delta_v_total for leg in legs]

    # Stacked bar showing each burn
    for i, leg in enumerate(legs):
        dv1 = leg.result.delta_v_1
        dv2 = leg.result.delta_v_2
        dv3 = leg.result.delta_v_3 or 0

        ax.bar(i, dv1, width=0.5, bottom=0, color=CYAN, alpha=0.8,
               edgecolor=CYAN_DIM, lw=0.5, zorder=3, label="B1" if i == 0 else "")
        ax.bar(i, dv2, width=0.5, bottom=dv1, color=AMBER, alpha=0.8,
               edgecolor=AMBER_DIM, lw=0.5, zorder=3, label="B2" if i == 0 else "")
        if dv3 > 0:
            ax.bar(i, dv3, width=0.5, bottom=dv1 + dv2, color=RED, alpha=0.6,
                   edgecolor=RED_DIM, lw=0.5, zorder=3,
                   label="B3" if i == 0 else "")

        # Total label on top
        ax.text(i, dvs[i] + max(dvs) * 0.03, f"{dvs[i]:.0f}",
                ha="center", fontsize=7, color=TEXT_PRIMARY,
                fontfamily="monospace",
                path_effects=_STROKE)

    ax.set_xticks(x_pos)
    ax.set_xticklabels([leg.name for leg in legs],
                        fontsize=7, fontfamily="monospace", color=TEXT_PRIMARY)
    ax.set_ylabel("\u0394v (m/s)", color=TEXT_DIM,
                   fontsize=8, fontfamily="monospace")
    ax.grid(True, axis="y", color=MPL_GRID, lw=0.3, alpha=0.4)

    # Summary text
    from vesper.widgets import _fmt_time
    ax.text(0.98, 0.95,
            f"TOTAL \u0394v: {total_dv:.0f} m/s\nTOTAL TIME: {_fmt_time(total_time)}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color=AMBER, fontfamily="monospace",
            fontweight="bold",
            path_effects=[pe.withStroke(linewidth=2, foreground=MPL_BG)])

    if n > 0:
        leg = ax.legend(loc="upper left", fontsize=7,
                         framealpha=0.15, edgecolor=MPL_GRID, facecolor=MPL_BG,
                         labelcolor=TEXT_DIM, borderpad=0.8)
        leg.get_frame().set_linewidth(0.5)
