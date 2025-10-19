"""Observability primitives for TraceFox services."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from services.shared.config import ConfigurationError, get_settings

try:  # Optional instrumentation helpers
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except ModuleNotFoundError:  # pragma: no cover - instrumentation is optional
    FastAPIInstrumentor = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class ObservabilityState:
    tracer_provider: Optional[TracerProvider] = None
    meter_provider: Optional[MeterProvider] = None


class ObservabilityManager:
    """Initialises OpenTelemetry tracing and metrics for a service."""

    def __init__(self) -> None:
        self._state = ObservabilityState()

    def configure(self, service_name: str) -> None:
        try:
            settings = get_settings()
            observability = settings.observability
        except ConfigurationError as exc:
            logger.warning("Observability configuration missing", exc_info=exc)
            return

        resource = Resource.create(
            {
                "service.name": service_name,
                "service.instance.id": os.getenv("TRACEFOX_INSTANCE_ID", str(uuid4())),
                "service.namespace": "tracefox",
                "deployment.environment": settings.environment,
            }
        )

        sampler = ParentBased(TraceIdRatioBased(observability.sampling_ratio))
        tracer_provider = TracerProvider(resource=resource, sampler=sampler)

        if observability.traces_endpoint:
            exporter = OTLPSpanExporter(endpoint=observability.traces_endpoint)
        else:
            exporter = ConsoleSpanExporter()

        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(tracer_provider)

        meter_provider = MeterProvider(resource=resource)
        metrics.set_meter_provider(meter_provider)

        self._state = ObservabilityState(tracer_provider=tracer_provider, meter_provider=meter_provider)

    def instrument_fastapi(self, app) -> None:  # type: ignore[no-untyped-def]
        if FastAPIInstrumentor is None:
            logger.debug("FastAPI instrumentation not available")
            return
        FastAPIInstrumentor.instrument_app(app)

    def tracer(self, component: str) -> trace.Tracer:
        return trace.get_tracer(component)

    def meter(self, component: str):  # type: ignore[no-untyped-def]
        provider = metrics.get_meter_provider()
        return provider.get_meter(component)

    def shutdown(self) -> None:
        if self._state.tracer_provider is not None:
            self._state.tracer_provider.shutdown()  # type: ignore[no-untyped-call]
        if self._state.meter_provider is not None:
            self._state.meter_provider.shutdown()  # type: ignore[no-untyped-call]
        self._state = ObservabilityState()


observability = ObservabilityManager()


__all__ = [
    "observability",
    "ObservabilityManager",
]

