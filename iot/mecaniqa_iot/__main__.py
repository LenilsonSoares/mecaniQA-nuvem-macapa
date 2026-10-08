import logging
import signal
from threading import Event, Thread

from .application import ReadingProcessor, simulate_readings
from .config import Settings
from .http import create_server
from .metrics import PrometheusMetrics


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_environment()
    stop = Event()
    metrics = PrometheusMetrics()
    processor = ReadingProcessor(metrics)
    server = create_server(("0.0.0.0", settings.port), processor, metrics, stop)

    def shutdown(signum: int, frame: object) -> None:
        if not stop.is_set():
            logging.info("Encerrando simulador: signal=%s", signum)
            stop.set()
            # shutdown precisa ocorrer fora da thread que executa serve_forever.
            Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    simulation = None
    if settings.simulation_interval > 0:
        simulation = Thread(
            target=simulate_readings,
            args=(
                processor,
                stop,
                settings.simulation_interval,
                settings.simulation_error_rate,
                settings.simulation_seed,
            ),
            daemon=True,
            name="sensor-simulator",
        )
        simulation.start()
    logging.info("Simulador disponível: port=%s", settings.port)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        stop.set()
        server.server_close()
        if simulation is not None:
            simulation.join(timeout=2)


if __name__ == "__main__":
    main()
