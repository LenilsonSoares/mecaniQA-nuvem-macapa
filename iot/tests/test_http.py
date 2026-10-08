import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from threading import Event, Thread

from mecaniqa_iot.application import ReadingProcessor
from mecaniqa_iot.http import create_server
from mecaniqa_iot.metrics import PrometheusMetrics


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stop = Event()
        cls.metrics = PrometheusMetrics()
        cls.server = create_server(
            ("127.0.0.1", 0), ReadingProcessor(cls.metrics), cls.metrics, cls.stop
        )
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None, content_type="application/json"):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, body, {"Content-Type": content_type})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_health_and_exact_routing(self):
        self.assertEqual(self.request("GET", "/health")[0], 200)
        for path in ("/healthXYZ", "/health/extra", "/metricsXYZ", "/missing"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("POST", "/health", "{}")[0], 405)

    def test_protocol_and_validation_errors(self):
        cases = [
            ("{}", "text/plain", 415),
            ("{", "application/json", 400),
            ("x" * 4097, "application/json", 413),
            ("{}", "application/json", 422),
        ]
        for body, content_type, status in cases:
            with self.subTest(status=status):
                self.assertEqual(self.request("POST", "/readings", body, content_type)[0], status)
        status, headers, _ = self.request("GET", "/readings")
        self.assertEqual((status, headers["Allow"]), (405, "POST"))

    def test_concurrent_readings_are_counted(self):
        registry = self.metrics.registry
        labels = {"result": "success", "source": "http"}
        before = registry.get_sample_value("mecaniqa_iot_readings_total", labels)
        payload = json.dumps({"sensor_type": "engine_temperature", "value": 90})
        with ThreadPoolExecutor(max_workers=8) as executor:
            responses = list(
                executor.map(lambda _: self.request("POST", "/readings", payload), range(40))
            )
        self.assertTrue(all(status == 200 for status, _, _ in responses))
        self.assertEqual(
            registry.get_sample_value("mecaniqa_iot_readings_total", labels) - before, 40
        )
        self.assertEqual(registry.get_sample_value("mecaniqa_iot_inflight_readings"), 0)

    def test_metrics_exposition(self):
        status, headers, body = self.request("GET", "/metrics")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", headers["Content-Type"])
        self.assertIn(b"process_resident_memory_bytes", body)
        self.assertIn(b"mecaniqa_iot_readings_total", body)

    def test_shutdown_reports_unavailable(self):
        self.stop.set()
        try:
            self.assertEqual(self.request("GET", "/health")[0], 503)
        finally:
            self.stop.clear()
