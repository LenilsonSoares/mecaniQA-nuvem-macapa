import math
import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    port: int = 8000
    simulation_interval: float = 1.0
    simulation_error_rate: float = 0.1
    simulation_seed: int = 42

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environment is None else environment
        settings = cls(
            port=int(env.get("PORT", "8000")),
            simulation_interval=float(env.get("SIMULATION_INTERVAL_SECONDS", "1")),
            simulation_error_rate=float(env.get("SIMULATION_ERROR_RATE", "0.1")),
            simulation_seed=int(env.get("SIMULATION_SEED", "42")),
        )
        if not 1 <= settings.port <= 65535:
            raise ValueError("PORT deve estar entre 1 e 65535.")
        interval = settings.simulation_interval
        if not math.isfinite(interval) or (interval != 0 and interval < 0.05):
            raise ValueError("SIMULATION_INTERVAL_SECONDS deve ser 0 ou pelo menos 0.05.")
        if not math.isfinite(settings.simulation_error_rate) or not (
            0 <= settings.simulation_error_rate <= 1
        ):
            raise ValueError("SIMULATION_ERROR_RATE deve estar entre 0 e 1.")
        return settings
