"""Adaptador Prometheus com rótulos limitados aos resultados e origens conhecidas."""

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    GCCollector,
    Histogram,
    PlatformCollector,
    ProcessCollector,
    generate_latest,
)

from .domain import SENSOR_RANGES, SensorReading


class PrometheusMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        ProcessCollector(registry=self.registry)
        PlatformCollector(registry=self.registry)
        GCCollector(registry=self.registry)
        self.readings = Counter(
            "mecaniqa_iot_readings_total",
            "Leituras processadas, separadas por resultado e origem.",
            ["result", "source"],
            registry=self.registry,
        )
        self.duration = Histogram(
            "mecaniqa_iot_processing_duration_seconds",
            "Tempo de validação e processamento das leituras em segundos.",
            ["result"],
            registry=self.registry,
        )
        self.inflight = Gauge(
            "mecaniqa_iot_inflight_readings",
            "Leituras em processamento neste processo.",
            registry=self.registry,
        )
        self.last_value = Gauge(
            "mecaniqa_iot_last_reading_value",
            "Último valor válido por tipo de sensor; unidades descritas no guia.",
            ["sensor_type"],
            registry=self.registry,
        )
        for result in ("success", "error"):
            self.duration.labels(result)
            for source in ("http", "simulator"):
                self.readings.labels(result, source)
        for sensor_type in SENSOR_RANGES:
            self.last_value.labels(sensor_type)

    def started(self) -> None:
        self.inflight.inc()

    def finished(
        self, result: str, source: str, duration: float, reading: SensorReading | None
    ) -> None:
        self.readings.labels(result, source).inc()
        self.duration.labels(result).observe(duration)
        if reading is not None:
            self.last_value.labels(reading.sensor_type).set(reading.value)
        self.inflight.dec()

    def render(self) -> bytes:
        return generate_latest(self.registry)
