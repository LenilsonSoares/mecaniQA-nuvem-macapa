import math
import unittest
from threading import Event

from mecaniqa_iot.application import ReadingProcessor, simulate_readings
from mecaniqa_iot.config import Settings
from mecaniqa_iot.domain import InvalidReading, SensorReading
from mecaniqa_iot.metrics import PrometheusMetrics


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.metrics = PrometheusMetrics()
        self.processor = ReadingProcessor(self.metrics)

    def test_accepts_boundaries(self):
        for value in (-40, 200):
            self.assertEqual(
                SensorReading.from_payload(
                    {"sensor_type": "engine_temperature", "value": value}
                ).value,
                value,
            )

    def test_rejects_invalid_sensor_and_values(self):
        payloads = [None, [], {}, {"sensor_type": "unknown", "value": 12}]
        payloads += [
            {"sensor_type": "battery_voltage", "value": value}
            for value in (True, "12", None, math.nan, math.inf, -1, 33, 10**400)
        ]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(InvalidReading):
                self.processor.process(payload)
        registry = self.metrics.registry
        self.assertEqual(registry.get_sample_value("mecaniqa_iot_inflight_readings"), 0)
        self.assertEqual(
            registry.get_sample_value(
                "mecaniqa_iot_readings_total", {"result": "error", "source": "http"}
            ),
            len(payloads),
        )

    def test_metrics_distinguish_success_errors_and_sources(self):
        self.processor.process({"sensor_type": "battery_voltage", "value": 12.4})
        with self.assertRaises(InvalidReading):
            self.processor.process({"sensor_type": "battery_voltage", "value": -1}, "simulator")
        registry = self.metrics.registry
        self.assertEqual(
            registry.get_sample_value(
                "mecaniqa_iot_readings_total", {"result": "success", "source": "http"}
            ),
            1,
        )
        self.assertEqual(
            registry.get_sample_value(
                "mecaniqa_iot_processing_duration_seconds_count", {"result": "error"}
            ),
            1,
        )
        self.assertEqual(
            registry.get_sample_value(
                "mecaniqa_iot_last_reading_value", {"sensor_type": "battery_voltage"}
            ),
            12.4,
        )
        self.assertEqual(registry.get_sample_value("mecaniqa_iot_inflight_readings"), 0)

    def test_simulator_respects_stop(self):
        stop = Event()
        stop.set()
        simulate_readings(self.processor, stop, 0.05, 1, 42)
        self.assertEqual(
            self.metrics.registry.get_sample_value(
                "mecaniqa_iot_readings_total", {"result": "error", "source": "simulator"}
            ),
            0,
        )

    def test_invalid_configuration_fails_before_startup(self):
        for env in (
            {"PORT": "0"},
            {"PORT": "65536"},
            {"PORT": "abc"},
            {"SIMULATION_INTERVAL_SECONDS": "nan"},
            {"SIMULATION_INTERVAL_SECONDS": "-1"},
            {"SIMULATION_INTERVAL_SECONDS": "0.01"},
            {"SIMULATION_ERROR_RATE": "1.1"},
            {"SIMULATION_ERROR_RATE": "inf"},
        ):
            with self.subTest(env=env), self.assertRaises(ValueError):
                Settings.from_environment(env)
        self.assertEqual(
            Settings.from_environment({"SIMULATION_INTERVAL_SECONDS": "0"}).simulation_interval, 0
        )
