# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
OpenTelemetry SDK Configurator for Easy Instrumentation with Distros
"""

import logging
import os
from abc import ABC, abstractmethod
from os import environ
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Type, Union

from typing_extensions import Literal

from opentelemetry._logs import set_logger_provider
from opentelemetry.environment_variables import (
    OTEL_LOGS_EXPORTER,
    OTEL_METRICS_EXPORTER,
    OTEL_PYTHON_ID_GENERATOR,
    OTEL_TRACES_EXPORTER,
)
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, LogExporter
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED,
    OTEL_EXPORTER_OTLP_LOGS_PROTOCOL,
    OTEL_EXPORTER_OTLP_METRICS_PROTOCOL,
    OTEL_EXPORTER_OTLP_PROTOCOL,
    OTEL_EXPORTER_OTLP_TRACES_PROTOCOL,
    OTEL_TRACES_SAMPLER,
    OTEL_TRACES_SAMPLER_ARG,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.sdk.trace.sampling import Sampler
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import set_tracer_provider
from opentelemetry.util._importlib_metadata import entry_points

_EXPORTER_OTLP = "otlp"
_EXPORTER_OTLP_PROTO_GRPC = "otlp_proto_grpc"
_EXPORTER_OTLP_PROTO_HTTP = "otlp_proto_http"

_EXPORTER_BY_OTLP_PROTOCOL = {
    "grpc": _EXPORTER_OTLP_PROTO_GRPC,
    "http/protobuf": _EXPORTER_OTLP_PROTO_HTTP,
}

_EXPORTER_ENV_BY_SIGNAL_TYPE = {
    "traces": OTEL_TRACES_EXPORTER,
    "metrics": OTEL_METRICS_EXPORTER,
    "logs": OTEL_LOGS_EXPORTER,
}

_PROTOCOL_ENV_BY_SIGNAL_TYPE = {
    "traces": OTEL_EXPORTER_OTLP_TRACES_PROTOCOL,
    "metrics": OTEL_EXPORTER_OTLP_METRICS_PROTOCOL,
    "logs": OTEL_EXPORTER_OTLP_LOGS_PROTOCOL,
}

_RANDOM_ID_GENERATOR = "random"
_DEFAULT_ID_GENERATOR = _RANDOM_ID_GENERATOR

_OTEL_SAMPLER_ENTRY_POINT_GROUP = "opentelemetry_traces_sampler"

_logger = logging.getLogger(__name__)


def _import_config_components(
    selected_components: List[str], entry_point_name: str
) -> Sequence[Tuple[str, object]]:

    component_implementations = []

    for selected_component in selected_components:
        try:
            component_implementations.append(
                (
                    selected_component,
                    next(
                        iter(
                            entry_points(
                                group=entry_point_name, name=selected_component
                            )
                        )
                    ).load(),
                )
            )
        except KeyError:

            raise RuntimeError(
                f"Requested entry point '{entry_point_name}' not found"
            )

        except StopIteration:

            raise RuntimeError(
                f"Requested component '{selected_component}' not found in "
                f"entry point '{entry_point_name}'"
            )

    return component_implementations


def _get_sampler() -> Optional[str]:
    return environ.get(OTEL_TRACES_SAMPLER, None)


def _get_id_generator() -> str:
    return environ.get(OTEL_PYTHON_ID_GENERATOR, _DEFAULT_ID_GENERATOR)


def _get_exporter_entry_point(
    exporter_name: str, signal_type: Literal["traces", "metrics", "logs"]
):
    if exporter_name not in (
        _EXPORTER_OTLP,
        _EXPORTER_OTLP_PROTO_GRPC,
        _EXPORTER_OTLP_PROTO_HTTP,
    ):
        return exporter_name

    # Checking env vars for OTLP protocol (grpc/http).
    otlp_protocol = environ.get(
        _PROTOCOL_ENV_BY_SIGNAL_TYPE[signal_type]
    ) or environ.get(OTEL_EXPORTER_OTLP_PROTOCOL)

    if not otlp_protocol:
        if exporter_name == _EXPORTER_OTLP:
            return _EXPORTER_OTLP_PROTO_GRPC
        return exporter_name

    otlp_protocol = otlp_protocol.strip()

    if exporter_name == _EXPORTER_OTLP:
        if otlp_protocol not in _EXPORTER_BY_OTLP_PROTOCOL:
            # Invalid value was set by the env var
            raise RuntimeError(
                f"Unsupported OTLP protocol '{otlp_protocol}' is configured"
            )

        return _EXPORTER_BY_OTLP_PROTOCOL[otlp_protocol]

    # grpc/http already specified by exporter_name, only add a warning in case
    # of a conflict.
    exporter_name_by_env = _EXPORTER_BY_OTLP_PROTOCOL.get(otlp_protocol)
    if exporter_name_by_env and exporter_name != exporter_name_by_env:
        _logger.warning(
            "Conflicting values for %s OTLP exporter protocol, using '%s'",
            signal_type,
            exporter_name,
        )

    return exporter_name


def _get_exporter_names(
    signal_type: Literal["traces", "metrics", "logs"]
) -> Sequence[str]:
    names = environ.get(_EXPORTER_ENV_BY_SIGNAL_TYPE.get(signal_type, ""))

    if not names or names.lower().strip() == "none":
        return []

    return [
        _get_exporter_entry_point(_exporter.strip(), signal_type)
        for _exporter in names.split(",")
    ]


def _init_tracing(
    exporters: Dict[str, Type[SpanExporter]],
    id_generator: IdGenerator = None,
    sampler: Sampler = None,
    resource: Resource = None,
):
    provider = TracerProvider(
        id_generator=id_generator,
        sampler=sampler,
        resource=resource,
    )
    set_tracer_provider(provider)

    for _, exporter_class in exporters.items():
        exporter_args = {}
        provider.add_span_processor(
            BatchSpanProcessor(exporter_class(**exporter_args))
        )


def _init_metrics(
    exporters_or_readers: Dict[
        str, Union[Type[MetricExporter], Type[MetricReader]]
    ],
    resource: Resource = None,
):
    metric_readers = []

    for _, exporter_or_reader_class in exporters_or_readers.items():
        exporter_args = {}

        if issubclass(exporter_or_reader_class, MetricReader):
            metric_readers.append(exporter_or_reader_class(**exporter_args))
        else:
            metric_readers.append(
                PeriodicExportingMetricReader(
                    exporter_or_reader_class(**exporter_args)
                )
            )

    provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    set_meter_provider(provider)


def _init_logging(
    exporters: Dict[str, Type[LogExporter]],
    resource: Resource = None,
):
    provider = LoggerProvider(resource=resource)
    set_logger_provider(provider)

    for _, exporter_class in exporters.items():
        exporter_args = {}
        provider.add_log_record_processor(
            BatchLogRecordProcessor(exporter_class(**exporter_args))
        )

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)

    logging.getLogger().addHandler(handler)


def _import_exporters(
    trace_exporter_names: Sequence[str],
    metric_exporter_names: Sequence[str],
    log_exporter_names: Sequence[str],
) -> Tuple[
    Dict[str, Type[SpanExporter]],
    Dict[str, Union[Type[MetricExporter], Type[MetricReader]]],
    Dict[str, Type[LogExporter]],
]:
    trace_exporters = {}
    metric_exporters = {}
    log_exporters = {}

    for (exporter_name, exporter_impl,) in _import_config_components(
        trace_exporter_names, "opentelemetry_traces_exporter"
    ):
        if issubclass(exporter_impl, SpanExporter):
            trace_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(f"{exporter_name} is not a trace exporter")

    for (exporter_name, exporter_impl,) in _import_config_components(
        metric_exporter_names, "opentelemetry_metrics_exporter"
    ):
        # The metric exporter components may be push MetricExporter or pull exporters which
        # subclass MetricReader directly
        if issubclass(exporter_impl, (MetricExporter, MetricReader)):
            metric_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(f"{exporter_name} is not a metric exporter")

    for (exporter_name, exporter_impl,) in _import_config_components(
        log_exporter_names, "opentelemetry_logs_exporter"
    ):
        if issubclass(exporter_impl, LogExporter):
            log_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(f"{exporter_name} is not a log exporter")

    return trace_exporters, metric_exporters, log_exporters


def _import_sampler_factory(sampler_name: str) -> Callable[[str], Sampler]:
    _, sampler_impl = _import_config_components(
        [sampler_name.strip()], _OTEL_SAMPLER_ENTRY_POINT_GROUP
    )[0]
    return sampler_impl


def _import_sampler(sampler_name: str) -> Optional[Sampler]:
    if not sampler_name:
        return None
    try:
        sampler_factory = _import_sampler_factory(sampler_name)
        arg = None
        if sampler_name in ("traceidratio", "parentbased_traceidratio"):
            try:
                rate = float(os.getenv(OTEL_TRACES_SAMPLER_ARG))
            except (ValueError, TypeError):
                _logger.warning(
                    "Could not convert TRACES_SAMPLER_ARG to float. Using default value 1.0."
                )
                rate = 1.0
            arg = rate
        else:
            arg = os.getenv(OTEL_TRACES_SAMPLER_ARG)

        sampler = sampler_factory(arg)
        if not isinstance(sampler, Sampler):
            message = f"Sampler factory, {sampler_factory}, produced output, {sampler}, which is not a Sampler."
            _logger.warning(message)
            raise ValueError(message)
        return sampler
    except Exception as exc:  # pylint: disable=broad-except
        _logger.warning(
            "Using default sampler. Failed to initialize sampler, %s: %s",
            sampler_name,
            exc,
        )
        return None


def _import_id_generator(id_generator_name: str) -> IdGenerator:
    id_generator_name, id_generator_impl = _import_config_components(
        [id_generator_name.strip()], "opentelemetry_id_generator"
    )[0]

    if issubclass(id_generator_impl, IdGenerator):
        return id_generator_impl()

    raise RuntimeError(f"{id_generator_name} is not an IdGenerator")


def _initialize_components(auto_instrumentation_version):
    trace_exporters, metric_exporters, log_exporters = _import_exporters(
        _get_exporter_names("traces"),
        _get_exporter_names("metrics"),
        _get_exporter_names("logs"),
    )
    sampler_name = _get_sampler()
    sampler = _import_sampler(sampler_name)
    id_generator_name = _get_id_generator()
    id_generator = _import_id_generator(id_generator_name)
    # if env var OTEL_RESOURCE_ATTRIBUTES is given, it will read the service_name
    # from the env variable else defaults to "unknown_service"
    auto_resource = {}
    # populate version if using auto-instrumentation
    if auto_instrumentation_version:
        auto_resource[
            ResourceAttributes.TELEMETRY_AUTO_VERSION
        ] = auto_instrumentation_version
    resource = Resource.create(auto_resource)

    _init_tracing(
        exporters=trace_exporters,
        id_generator=id_generator,
        sampler=sampler,
        resource=resource,
    )
    _init_metrics(metric_exporters, resource)
    logging_enabled = os.getenv(
        _OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED, "false"
    )
    if logging_enabled.strip().lower() == "true":
        _init_logging(log_exporters, resource)


class _BaseConfigurator(ABC):
    """An ABC for configurators

    Configurators are used to configure
    SDKs (i.e. TracerProvider, MeterProvider, Processors...)
    to reduce the amount of manual configuration required.
    """

    _instance = None
    _is_instrumented = False

    def __new__(cls, *args, **kwargs):

        if cls._instance is None:
            cls._instance = object.__new__(cls, *args, **kwargs)

        return cls._instance

    @abstractmethod
    def _configure(self, **kwargs):
        """Configure the SDK"""

    def configure(self, **kwargs):
        """Configure the SDK"""
        self._configure(**kwargs)


class _OTelSDKConfigurator(_BaseConfigurator):
    """A basic Configurator by OTel Python for initializing OTel SDK components

    Initializes several crucial OTel SDK components (i.e. TracerProvider,
    MeterProvider, Processors...) according to a default implementation. Other
    Configurators can subclass and slightly alter this initialization.

    NOTE: This class should not be instantiated nor should it become an entry
    point on the `opentelemetry-sdk` package. Instead, distros should subclass
    this Configurator and enhance it as needed.
    """

    def _configure(self, **kwargs):
        _initialize_components(kwargs.get("auto_instrumentation_version"))
