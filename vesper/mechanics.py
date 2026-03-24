"""
VESPER orbital mechanics — two-body Keplerian calculations.

All altitudes are in km above Earth's surface.
All delta-v results are in m/s.
All times are in seconds (converted for display elsewhere).

Simplifications:
  - Circular initial and target orbits only
  - Earth-centred, two-body only
  - No perturbations, atmosphere, or J2
  - Plane changes modelled as simple combined or standalone burns
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional

# ── Constants ───────────────────────────────────────────────────────────────

MU_EARTH = 3.986004418e14   # m^3/s^2 — Earth's gravitational parameter
R_EARTH = 6_371_000.0       # m — mean Earth radius


@dataclass
class TransferResult:
    """Results of an orbital transfer calculation."""
    name: str
    delta_v_1: float          # m/s — first burn
    delta_v_2: float          # m/s — second burn
    delta_v_3: Optional[float]  # m/s — third burn (bi-elliptic only)
    delta_v_total: float      # m/s
    transfer_time: float      # seconds
    # Geometry for plotting
    a_transfer_1: float       # m — semi-major axis of first transfer ellipse
    e_transfer_1: float       # eccentricity of first transfer ellipse
    a_transfer_2: Optional[float]  # for bi-elliptic
    e_transfer_2: Optional[float]


def orbital_velocity(r: float) -> float:
    """Circular orbital velocity at radius r (m) from Earth centre."""
    return np.sqrt(MU_EARTH / r)


def alt_to_radius(alt_km: float) -> float:
    """Convert altitude in km to radius in metres."""
    return (alt_km * 1000.0) + R_EARTH


def hohmann_transfer(r1: float, r2: float, delta_inc_deg: float = 0.0) -> TransferResult:
    """
    Compute a Hohmann transfer between two circular orbits.

    If delta_inc_deg > 0, the plane change is combined with the second
    (circularisation) burn at apoapsis — this is the optimal split for
    pure Hohmann when raising orbit.

    Parameters:
        r1: radius of initial orbit (m)
        r2: radius of target orbit (m)
        delta_inc_deg: inclination change (degrees)
    """
    v1 = orbital_velocity(r1)
    v2 = orbital_velocity(r2)

    a_t = (r1 + r2) / 2.0
    e_t = abs(r2 - r1) / (r1 + r2)

    # Velocities on the transfer ellipse
    v_t_peri = np.sqrt(MU_EARTH * (2.0 / r1 - 1.0 / a_t))
    v_t_apo = np.sqrt(MU_EARTH * (2.0 / r2 - 1.0 / a_t))

    dv1 = abs(v_t_peri - v1)

    if delta_inc_deg > 0:
        # Combine plane change with circularisation burn at apoapsis
        delta_inc_rad = np.radians(delta_inc_deg)
        dv2 = np.sqrt(v2**2 + v_t_apo**2
                       - 2.0 * v2 * v_t_apo * np.cos(delta_inc_rad))
    else:
        dv2 = abs(v2 - v_t_apo)

    T_transfer = np.pi * np.sqrt(a_t**3 / MU_EARTH)

    return TransferResult(
        name="Hohmann" + (" + Plane Change" if delta_inc_deg > 0 else ""),
        delta_v_1=dv1,
        delta_v_2=dv2,
        delta_v_3=None,
        delta_v_total=dv1 + dv2,
        transfer_time=T_transfer,
        a_transfer_1=a_t,
        e_transfer_1=e_t,
        a_transfer_2=None,
        e_transfer_2=None,
    )


def bielliptic_transfer(r1: float, r2: float,
                         r_intermediate_factor: float = 1.5,
                         delta_inc_deg: float = 0.0) -> TransferResult:
    """
    Compute a bi-elliptic transfer between two circular orbits.

    The intermediate radius is set as r_intermediate_factor * max(r1, r2).
    Plane change, if any, is split and applied at the intermediate (highest) point.

    Parameters:
        r1: radius of initial orbit (m)
        r2: radius of target orbit (m)
        r_intermediate_factor: multiplier for intermediate apoapsis
        delta_inc_deg: inclination change (degrees)
    """
    r_b = r_intermediate_factor * max(r1, r2)

    v1 = orbital_velocity(r1)
    v2 = orbital_velocity(r2)

    # First ellipse: r1 → r_b
    a1 = (r1 + r_b) / 2.0
    e1 = abs(r_b - r1) / (r1 + r_b)
    v_t1_peri = np.sqrt(MU_EARTH * (2.0 / r1 - 1.0 / a1))
    v_t1_apo = np.sqrt(MU_EARTH * (2.0 / r_b - 1.0 / a1))

    # Second ellipse: r_b → r2
    a2 = (r_b + r2) / 2.0
    e2 = abs(r_b - r2) / (r_b + r2)
    v_t2_apo = np.sqrt(MU_EARTH * (2.0 / r_b - 1.0 / a2))
    v_t2_peri = np.sqrt(MU_EARTH * (2.0 / r2 - 1.0 / a2))

    dv1 = abs(v_t1_peri - v1)

    if delta_inc_deg > 0:
        # Apply plane change at intermediate point (most efficient)
        delta_inc_rad = np.radians(delta_inc_deg)
        dv2 = np.sqrt(v_t1_apo**2 + v_t2_apo**2
                       - 2.0 * v_t1_apo * v_t2_apo * np.cos(delta_inc_rad))
    else:
        dv2 = abs(v_t2_apo - v_t1_apo)

    dv3 = abs(v2 - v_t2_peri)

    T1 = np.pi * np.sqrt(a1**3 / MU_EARTH)
    T2 = np.pi * np.sqrt(a2**3 / MU_EARTH)

    return TransferResult(
        name="Bi-elliptic" + (" + Plane Change" if delta_inc_deg > 0 else ""),
        delta_v_1=dv1,
        delta_v_2=dv2,
        delta_v_3=dv3,
        delta_v_total=dv1 + dv2 + dv3,
        transfer_time=T1 + T2,
        a_transfer_1=a1,
        e_transfer_1=e1,
        a_transfer_2=a2,
        e_transfer_2=e2,
    )


def compute_transfers(alt_init_km: float, alt_target_km: float,
                      delta_inc_deg: float = 0.0) -> list[TransferResult]:
    """
    Compute all available transfer options for the given inputs.
    Returns a list of TransferResult sorted by total delta-v.
    """
    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)

    if r1 <= 0 or r2 <= 0 or r1 == r2:
        return []

    results = []

    # Hohmann (no plane change)
    results.append(hohmann_transfer(r1, r2, delta_inc_deg=0.0))

    # Bi-elliptic (no plane change)
    results.append(bielliptic_transfer(r1, r2, delta_inc_deg=0.0))

    # With plane change variants
    if delta_inc_deg > 0:
        results.append(hohmann_transfer(r1, r2, delta_inc_deg=delta_inc_deg))
        results.append(bielliptic_transfer(r1, r2, delta_inc_deg=delta_inc_deg))

    results.sort(key=lambda r: r.delta_v_total)
    return results


def sweep_target_altitude(alt_init_km: float,
                           alt_range_km: tuple[float, float] = (300, 50000),
                           n_points: int = 200,
                           delta_inc_deg: float = 0.0):
    """
    Sweep target altitude and return delta-v data for Hohmann and bi-elliptic.

    Returns:
        altitudes: array of target altitudes in km
        dv_hohmann: array of total Hohmann delta-v in m/s
        dv_bielliptic: array of total bi-elliptic delta-v in m/s
    """
    r1 = alt_to_radius(alt_init_km)
    altitudes = np.linspace(alt_range_km[0], alt_range_km[1], n_points)

    dv_hohmann = np.zeros(n_points)
    dv_bielliptic = np.zeros(n_points)

    for i, alt in enumerate(altitudes):
        r2 = alt_to_radius(alt)
        if r2 == r1:
            dv_hohmann[i] = 0
            dv_bielliptic[i] = 0
            continue
        h = hohmann_transfer(r1, r2, delta_inc_deg)
        b = bielliptic_transfer(r1, r2, delta_inc_deg=delta_inc_deg)
        dv_hohmann[i] = h.delta_v_total
        dv_bielliptic[i] = b.delta_v_total

    return altitudes, dv_hohmann, dv_bielliptic
