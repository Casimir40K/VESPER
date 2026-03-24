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


# ── Sweep functions ──────────────────────────────────────────────────────────

def sweep_inclination(alt_init_km: float, alt_target_km: float,
                      inc_range: tuple[float, float] = (0, 60),
                      n_points: int = 100):
    """
    Sweep inclination change and return delta-v for both methods.

    Returns:
        inclinations_deg: array of inclination changes in degrees
        dv_hohmann: array of total Hohmann delta-v in m/s
        dv_bielliptic: array of total bi-elliptic delta-v in m/s
    """
    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)

    inclinations_deg = np.linspace(inc_range[0], inc_range[1], n_points)
    dv_hohmann = np.zeros(n_points)
    dv_bielliptic = np.zeros(n_points)

    for i, inc in enumerate(inclinations_deg):
        h = hohmann_transfer(r1, r2, delta_inc_deg=inc)
        b = bielliptic_transfer(r1, r2, delta_inc_deg=inc)
        dv_hohmann[i] = h.delta_v_total
        dv_bielliptic[i] = b.delta_v_total

    return inclinations_deg, dv_hohmann, dv_bielliptic


def sweep_intermediate(alt_init_km: float, alt_target_km: float,
                       factor_range: tuple[float, float] = (1.1, 3.0),
                       n_points: int = 100,
                       delta_inc_deg: float = 0.0):
    """
    Sweep bi-elliptic intermediate apoapsis factor.

    Returns:
        factors: array of intermediate radius factors
        dv_bielliptic: array of total bi-elliptic delta-v in m/s

    Also computes the Hohmann delta-v as a constant reference value;
    retrieve it via hohmann_transfer directly if needed for comparison.
    """
    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)

    factors = np.linspace(factor_range[0], factor_range[1], n_points)
    dv_bielliptic = np.zeros(n_points)

    for i, f in enumerate(factors):
        b = bielliptic_transfer(r1, r2, r_intermediate_factor=f,
                                delta_inc_deg=delta_inc_deg)
        dv_bielliptic[i] = b.delta_v_total

    return factors, dv_bielliptic


def sweep_transfer_time(alt_init_km: float,
                        alt_range_km: tuple[float, float] = (200, 50000),
                        n_points: int = 100):
    """
    Sweep target altitude and return transfer times.

    Returns:
        altitudes: array of target altitudes in km
        time_hohmann_hours: array of Hohmann transfer times in hours
        time_bielliptic_hours: array of bi-elliptic transfer times in hours
    """
    r1 = alt_to_radius(alt_init_km)
    altitudes = np.linspace(alt_range_km[0], alt_range_km[1], n_points)

    time_hohmann_hours = np.zeros(n_points)
    time_bielliptic_hours = np.zeros(n_points)

    for i, alt in enumerate(altitudes):
        r2 = alt_to_radius(alt)
        if r2 == r1:
            continue
        h = hohmann_transfer(r1, r2)
        b = bielliptic_transfer(r1, r2)
        time_hohmann_hours[i] = h.transfer_time / 3600.0
        time_bielliptic_hours[i] = b.transfer_time / 3600.0

    return altitudes, time_hohmann_hours, time_bielliptic_hours


# ── Plane change comparison ──────────────────────────────────────────────────

@dataclass
class PlaneChangeStrategy:
    """Describes one plane-change + transfer strategy."""
    name: str
    delta_v_total: float        # m/s
    delta_v_transfer: float     # m/s — orbit-raising portion
    delta_v_plane_change: float # m/s — plane-change portion
    description: str


def compare_plane_changes(alt_init_km: float, alt_target_km: float,
                          delta_inc_deg: float) -> list[PlaneChangeStrategy]:
    """
    Compare four plane-change strategies and return them sorted by total
    delta-v (lowest first).

    Strategies:
        1. Plane change at initial orbit + Hohmann transfer (no inc change)
        2. Hohmann transfer + plane change at target orbit
        3. Hohmann with combined plane change at apoapsis
        4. Bi-elliptic with plane change at intermediate point

    Returns an empty list if delta_inc_deg <= 0.
    """
    if delta_inc_deg <= 0:
        return []

    r1 = alt_to_radius(alt_init_km)
    r2 = alt_to_radius(alt_target_km)
    delta_inc_rad = np.radians(delta_inc_deg)

    v1 = orbital_velocity(r1)
    v2 = orbital_velocity(r2)

    hohmann_no_inc = hohmann_transfer(r1, r2, delta_inc_deg=0.0)

    # Strategy 1: Plane change at initial orbit, then Hohmann
    dv_plane_1 = 2.0 * v1 * np.sin(delta_inc_rad / 2.0)
    dv_transfer_1 = hohmann_no_inc.delta_v_total
    s1 = PlaneChangeStrategy(
        name="Plane change at LEO + Hohmann",
        delta_v_total=dv_plane_1 + dv_transfer_1,
        delta_v_transfer=dv_transfer_1,
        delta_v_plane_change=dv_plane_1,
        description="Perform full plane change at initial orbit, then raise orbit via Hohmann.",
    )

    # Strategy 2: Hohmann, then plane change at target orbit
    dv_plane_2 = 2.0 * v2 * np.sin(delta_inc_rad / 2.0)
    dv_transfer_2 = hohmann_no_inc.delta_v_total
    s2 = PlaneChangeStrategy(
        name="Hohmann + Plane change at target",
        delta_v_total=dv_plane_2 + dv_transfer_2,
        delta_v_transfer=dv_transfer_2,
        delta_v_plane_change=dv_plane_2,
        description="Raise orbit via Hohmann, then perform full plane change at target orbit.",
    )

    # Strategy 3: Combined Hohmann with plane change at apoapsis
    hohmann_combined = hohmann_transfer(r1, r2, delta_inc_deg=delta_inc_deg)
    dv_combined_transfer = hohmann_no_inc.delta_v_total
    s3 = PlaneChangeStrategy(
        name="Hohmann with combined plane change",
        delta_v_total=hohmann_combined.delta_v_total,
        delta_v_transfer=hohmann_combined.delta_v_1,
        delta_v_plane_change=hohmann_combined.delta_v_total - hohmann_combined.delta_v_1,
        description="Combine circularisation and plane change into a single burn at apoapsis.",
    )

    # Strategy 4: Bi-elliptic with plane change at intermediate point
    bielliptic_combined = bielliptic_transfer(r1, r2, delta_inc_deg=delta_inc_deg)
    bielliptic_no_inc = bielliptic_transfer(r1, r2, delta_inc_deg=0.0)
    s4 = PlaneChangeStrategy(
        name="Bi-elliptic with plane change",
        delta_v_total=bielliptic_combined.delta_v_total,
        delta_v_transfer=bielliptic_no_inc.delta_v_total,
        delta_v_plane_change=bielliptic_combined.delta_v_total - bielliptic_no_inc.delta_v_total,
        description="Use bi-elliptic transfer with plane change at the intermediate apoapsis.",
    )

    strategies = [s1, s2, s3, s4]
    strategies.sort(key=lambda s: s.delta_v_total)
    return strategies


# ── Mission chain ────────────────────────────────────────────────────────────

@dataclass
class MissionLeg:
    """One leg of a multi-burn mission chain."""
    name: str
    alt_init_km: float
    alt_target_km: float
    delta_inc_deg: float
    result: TransferResult


def compute_mission_chain(legs_spec: list[tuple[str, float, float, float]]):
    """
    Compute a sequence of orbital transfers.

    Parameters:
        legs_spec: list of (name, alt_init_km, alt_target_km, delta_inc_deg) tuples

    Returns:
        legs: list of MissionLeg (one per spec entry)
        total_dv: total delta-v across all legs (m/s)
        total_time: total transfer time across all legs (seconds)

    For each leg the best transfer (lowest delta-v from compute_transfers)
    is selected.
    """
    legs: list[MissionLeg] = []
    total_dv = 0.0
    total_time = 0.0

    for name, alt_init, alt_target, delta_inc in legs_spec:
        results = compute_transfers(alt_init, alt_target, delta_inc)
        if not results:
            continue
        best = results[0]  # already sorted by delta_v_total
        leg = MissionLeg(
            name=name,
            alt_init_km=alt_init,
            alt_target_km=alt_target,
            delta_inc_deg=delta_inc,
            result=best,
        )
        legs.append(leg)
        total_dv += best.delta_v_total
        total_time += best.transfer_time

    return legs, total_dv, total_time
