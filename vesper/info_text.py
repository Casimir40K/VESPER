"""VESPER method explanations and educational content."""

INFO_SECTIONS = [
    {
        "key": "hohmann",
        "title": "HOHMANN TRANSFER",
        "content": (
            "The Hohmann transfer is the most fuel-efficient two-impulse "
            "manoeuvre for moving between two coplanar circular orbits.\n\n"
            "PROCEDURE:\n"
            "  1. Burn prograde at periapsis to enter an elliptical\n"
            "     transfer orbit whose apoapsis touches the target orbit\n"
            "  2. At apoapsis, burn prograde again to circularise\n"
            "     into the target orbit\n\n"
            "CHARACTERISTICS:\n"
            "  - Always uses exactly 2 burns\n"
            "  - Minimum delta-v for most orbit-raising scenarios\n"
            "  - Transfer time = half the period of the transfer ellipse\n"
            "  - Optimal when the ratio r2/r1 < 11.94"
        ),
    },
    {
        "key": "bielliptic",
        "title": "BI-ELLIPTIC TRANSFER",
        "content": (
            "The bi-elliptic transfer uses three burns and an intermediate\n"
            "orbit that overshoots the target, then drops back down.\n\n"
            "PROCEDURE:\n"
            "  1. Burn prograde to enter a highly elliptical orbit\n"
            "     with apoapsis above the target\n"
            "  2. At the intermediate apoapsis, burn to adjust the\n"
            "     periapsis to match the target orbit radius\n"
            "  3. At the new periapsis (target radius), circularise\n\n"
            "CHARACTERISTICS:\n"
            "  - Uses 3 burns (more complex operationally)\n"
            "  - Can beat Hohmann when r2/r1 > 11.94\n"
            "  - Much longer transfer time\n"
            "  - Excellent for combining with plane changes\n"
            "     (plane change at high altitude is cheap)"
        ),
    },
    {
        "key": "plane_change",
        "title": "PLANE CHANGES",
        "content": (
            "Changing orbital inclination requires a velocity component\n"
            "perpendicular to the current orbit plane. This is expensive\n"
            "because it scales with orbital velocity.\n\n"
            "KEY INSIGHT:\n"
            "  delta-v_plane = 2 * v * sin(delta_i / 2)\n\n"
            "Since v is lower at higher altitudes, plane changes are\n"
            "much cheaper when performed at apoapsis. A 28.5 deg plane\n"
            "change at LEO (400 km) costs ~3,800 m/s, but at GEO\n"
            "altitude it costs only ~1,500 m/s.\n\n"
            "STRATEGIES:\n"
            "  - Plane change at departure orbit (expensive)\n"
            "  - Plane change at arrival orbit\n"
            "  - Combined with circularisation burn (often optimal)\n"
            "  - At bi-elliptic intermediate point (cheapest for\n"
            "    large plane changes with large orbit raises)"
        ),
    },
    {
        "key": "assumptions",
        "title": "MODEL ASSUMPTIONS",
        "content": (
            "VESPER uses a simplified two-body Keplerian model.\n\n"
            "ASSUMPTIONS:\n"
            "  - Earth is a perfect sphere (no J2 oblateness)\n"
            "  - No atmospheric drag\n"
            "  - No third-body perturbations (Moon, Sun)\n"
            "  - All burns are impulsive (instantaneous)\n"
            "  - Initial and target orbits are circular\n"
            "     (unless elliptical mode is enabled)\n"
            "  - Earth gravitational parameter:\n"
            "     mu = 3.986e14 m^3/s^2\n"
            "  - Earth mean radius: 6371 km\n\n"
            "These simplifications are standard for preliminary\n"
            "mission design and trade studies. Real missions require\n"
            "high-fidelity propagation with perturbation models."
        ),
    },
    {
        "key": "crossover",
        "title": "HOHMANN vs BI-ELLIPTIC CROSSOVER",
        "content": (
            "For orbit ratio r2/r1 < 11.94, Hohmann is always cheaper.\n"
            "Above this ratio, bi-elliptic CAN be cheaper depending on\n"
            "the intermediate orbit altitude chosen.\n\n"
            "The crossover is most significant when:\n"
            "  - Large altitude ratio (LEO to very high orbit)\n"
            "  - Combined with large plane changes\n"
            "  - Transfer time is not a constraint\n\n"
            "The trade study plots show this crossover clearly:\n"
            "when the amber (bi-elliptic) curve drops below the\n"
            "cyan (Hohmann) curve, bi-elliptic becomes favourable.\n\n"
            "In practice, bi-elliptic is rarely used for pure altitude\n"
            "changes because the time penalty is severe. It becomes\n"
            "practical when combined with large plane changes, since\n"
            "the high intermediate orbit makes the plane change cheap."
        ),
    },
]
