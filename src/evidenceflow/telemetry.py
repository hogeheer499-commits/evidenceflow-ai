from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class Telemetry:
    counters: Counter[str] = field(default_factory=Counter)
    durations_ms: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str) -> None:
        self.counters[name] += 1

    @contextmanager
    def measure(self, name: str) -> Iterator[None]:
        started = perf_counter()
        try:
            yield
        finally:
            elapsed = (perf_counter() - started) * 1000
            self.durations_ms.setdefault(name, []).append(elapsed)

    def snapshot(self) -> dict[str, object]:
        return {
            "counters": dict(self.counters),
            "durations_ms": self.durations_ms,
        }


class OpenTelemetryTelemetry(Telemetry):
    """Mirror local measurements to an externally configured OTel provider."""

    def __init__(self, instrumentation_name: str = "evidenceflow") -> None:
        super().__init__()
        try:
            from opentelemetry import metrics, trace
        except ImportError as exc:
            raise RuntimeError(
                "install the 'telemetry' extra to enable OpenTelemetry"
            ) from exc
        self._meter = metrics.get_meter(instrumentation_name)
        self._tracer = trace.get_tracer(instrumentation_name)
        self._otel_counters: dict[str, object] = {}
        self._otel_histograms: dict[str, object] = {}

    def increment(self, name: str) -> None:
        super().increment(name)
        if name not in self._otel_counters:
            self._otel_counters[name] = self._meter.create_counter(
                f"evidenceflow.{name}"
            )
        counter = self._otel_counters[name]
        counter.add(1)

    @contextmanager
    def measure(self, name: str) -> Iterator[None]:
        started = perf_counter()
        with self._tracer.start_as_current_span(f"evidenceflow.{name}"):
            try:
                yield
            finally:
                elapsed = (perf_counter() - started) * 1000
                self.durations_ms.setdefault(name, []).append(elapsed)
                if name not in self._otel_histograms:
                    self._otel_histograms[name] = self._meter.create_histogram(
                        f"evidenceflow.{name}.duration", unit="ms"
                    )
                histogram = self._otel_histograms[name]
                histogram.record(elapsed)
