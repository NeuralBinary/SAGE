from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from .config import Settings


class Telemetry:
    """Optional OpenTelemetry bridge using GenAI-style operation naming.

    SAGE-specific measurements stay under the `sage.*` namespace while model usage
    can coexist with standard `gen_ai.*` attributes emitted by provider SDKs.
    """

    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.otel_enabled
        self._trace = None
        self._meter = None
        if self.enabled:
            try:
                from opentelemetry import metrics, trace
                self._trace = trace.get_tracer(settings.otel_service_name)
                self._meter = metrics.get_meter(settings.otel_service_name)
            except Exception:
                self.enabled = False
        self._counters: dict[str, Any] = {}

    @contextmanager
    def span(self, operation: str, **attrs: Any) -> Iterator[Any]:
        if not self.enabled or self._trace is None:
            yield None
            return
        with self._trace.start_as_current_span(f"sage.{operation}") as span:
            span.set_attribute("gen_ai.operation.name", operation)
            for key, value in attrs.items():
                if value is not None and isinstance(value, (str, bool, int, float)):
                    span.set_attribute(f"sage.{key}", value)
            yield span

    def add(self, name: str, value: int | float, **attrs: Any) -> None:
        if not self.enabled or self._meter is None:
            return
        counter = self._counters.get(name)
        if counter is None:
            counter = self._meter.create_counter(f"sage.{name}")
            self._counters[name] = counter
        safe_attrs = {f"sage.{k}": v for k, v in attrs.items() if isinstance(v, (str, bool, int, float))}
        counter.add(value, safe_attrs)
