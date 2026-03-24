"""VESPER scenario management — save, compare, and manage orbital transfer scenarios."""

from dataclasses import dataclass, field
from datetime import datetime
from vesper.mechanics import TransferResult, compute_transfers


@dataclass
class Scenario:
    """A saved orbital transfer scenario for comparison."""
    name: str
    alt_init_km: float
    alt_target_km: float
    delta_inc_deg: float
    best_dv: float          # m/s
    best_method: str
    best_time: float        # seconds
    n_burns: int
    transfers: list  # list of TransferResult (not type-annotated to avoid issues)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")


class ScenarioManager:
    """Manages a collection of saved scenarios for comparison."""

    MAX_SCENARIOS = 8

    def __init__(self):
        self._scenarios: list[Scenario] = []

    def save(self, name, alt_init_km, alt_target_km, delta_inc_deg):
        """Save current parameters as a scenario. Returns the Scenario."""
        transfers = compute_transfers(alt_init_km, alt_target_km, delta_inc_deg)
        if not transfers:
            return None

        best = transfers[0]
        n_burns = 3 if best.delta_v_3 is not None else 2

        scenario = Scenario(
            name=name,
            alt_init_km=alt_init_km,
            alt_target_km=alt_target_km,
            delta_inc_deg=delta_inc_deg,
            best_dv=best.delta_v_total,
            best_method=best.name,
            best_time=best.transfer_time,
            n_burns=n_burns,
            transfers=transfers,
        )

        if len(self._scenarios) >= self.MAX_SCENARIOS:
            self._scenarios.pop(0)  # Remove oldest

        self._scenarios.append(scenario)
        return scenario

    def remove(self, index):
        if 0 <= index < len(self._scenarios):
            self._scenarios.pop(index)

    def clear(self):
        self._scenarios.clear()

    @property
    def scenarios(self):
        return list(self._scenarios)

    @property
    def count(self):
        return len(self._scenarios)
