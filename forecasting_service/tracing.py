import os

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.trace.propagation import set_span_in_context

if os.environ.get("POD_NAME"):
    pod_name = os.environ.get("POD_NAME")
else:
    pod_name = "ForecastingService"

trace.set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: pod_name}))
)


class TracingClient:
    def __init__(self, host, port) -> None:
        self.host = host
        self.port = port

        if host and port:
            self.jaeger_exporter = JaegerExporter(
                agent_host_name=host,
                agent_port=port,
            )
        else:
            self.jaeger_exporter = None

        self._tracer = None

    def create_instance(self, tracer_name):
        if self.jaeger_exporter:
            trace.get_tracer_provider().add_span_processor(
                BatchSpanProcessor(self.jaeger_exporter)
            )
            self._tracer = trace.get_tracer(tracer_name)

    def trace_as_current(
        self, span_name, verbose=1, kind=trace.SpanKind.INTERNAL, context=None, **kwargs
    ):
        if self._tracer and verbose == 1:
            if "epoch_no" in kwargs:
                span_name = f"Epoch-{kwargs['epoch_no']}-{span_name}"
            if hasattr(self, "_parent_span"):
                context = set_span_in_context(self._parent_span)
            return self._tracer.start_as_current_span(
                span_name, context=context, kind=kind
            )
        else:
            return DummySpan()

    def trace(
        self, span_name, verbose=1, kind=trace.SpanKind.INTERNAL, context=None, **kwargs
    ):
        if self._tracer and verbose == 1:
            if "epoch_no" in kwargs:
                span_name = f"Epoch-{kwargs['epoch_no']}-{span_name}"
            if hasattr(self, "_parent_span"):
                context = set_span_in_context(self._parent_span)
            return self._tracer.start_span(span_name, context=context, kind=kind)
        else:
            return DummySpan()

    def set_attribute(self, name, value):
        trace.get_current_span().set_attribute(name, value)


class DummySpan:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self
