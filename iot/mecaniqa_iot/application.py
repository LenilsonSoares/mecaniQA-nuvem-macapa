"""Processamento das leituras e geração de tráfego sintético."""

import logging
import random
from threading import Event
from time import perf_counter
from typing import Protocol

from .domain import InvalidReading, SensorReading

LOGGER = logging.getLogger(__name__)


class ReadingObserver(Protocol):
    def started(self) -> None: ...

    def finished(
        self, result: str, source: str, duration: float, reading: SensorReading | None
    ) -> None: ...


class ReadingProcessor:
    def __init__(self, observer: ReadingObserver) -> None:
        self._observer = observer

    def process(self, payload: object, source: str = "http") -> SensorReading:
        if source not in {"http", "simulator"}:
            raise ValueError("Origem de leitura desconhecida.")
        started_at = perf_counter()
        self._observer.started()
        reading = None
        result = "error"
        try:
            reading = SensorReading.from_payload(payload)
            result = "success"
            return reading
        finally:
            self._observer.finished(result, source, perf_counter() - started_at, reading)


def simulate_readings(
    processor: ReadingProcessor, stop: Event, interval: float, error_rate: float, seed: int
) -> None:
    random_source = random.Random(seed)
    while not stop.is_set():
        sensor_type = random_source.choice(("engine_temperature", "battery_voltage"))
        value = (
            random_source.uniform(70, 110)
            if sensor_type == "engine_temperature"
            else random_source.uniform(11.5, 14.8)
        )
        # Entradas inválidas exercitam o mesmo caminho de erro utilizado pela API.
        if random_source.random() < error_rate:
            value = -100.0
        try:
            processor.process({"sensor_type": sensor_type, "value": value}, source="simulator")
        except InvalidReading:
            LOGGER.info("Leitura sintética rejeitada: sensor_type=%s", sensor_type)
        stop.wait(interval)
