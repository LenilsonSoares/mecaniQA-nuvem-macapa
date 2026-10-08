"""Regras de leitura independentes de HTTP, Prometheus e Kubernetes."""

import math
from dataclasses import dataclass

# Faixas de plausibilidade do simulador, não limites de diagnóstico automotivo.
SENSOR_RANGES = {
    "engine_temperature": (-40.0, 200.0),
    "battery_voltage": (0.0, 32.0),
}


class InvalidReading(ValueError):
    pass


@dataclass(frozen=True)
class SensorReading:
    sensor_type: str
    value: float

    @classmethod
    def from_payload(cls, payload: object) -> "SensorReading":
        if not isinstance(payload, dict):
            raise InvalidReading("A leitura deve ser um objeto JSON.")
        sensor_type = payload.get("sensor_type")
        if not isinstance(sensor_type, str) or sensor_type not in SENSOR_RANGES:
            raise InvalidReading("sensor_type deve ser engine_temperature ou battery_voltage.")
        value = payload.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidReading("value deve ser um número finito.")
        try:
            number = float(value)
        except OverflowError as error:
            raise InvalidReading("value excede a faixa numérica suportada.") from error
        if not math.isfinite(number):
            raise InvalidReading("value deve ser um número finito.")
        lower, upper = SENSOR_RANGES[sensor_type]
        if not lower <= number <= upper:
            raise InvalidReading(f"value deve estar entre {lower} e {upper}.")
        return cls(sensor_type=sensor_type, value=number)
