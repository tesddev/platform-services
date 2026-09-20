# Known Issues

## Distributed tracing: auth-service and notification-service spans
not reaching Tempo

**Status:** Unresolved, root cause narrowed but not fixed.

The OTel tracing pipeline (SDK → OTLP gRPC exporter → Tempo → Grafana)
is confirmed fully working end-to-end for api-gateway: traces appear in
Tempo's search and waterfall view with correct timing and status data.

auth-service and notification-service run identical instrumentation
code (same middleware, same TracerProvider/OTLPSpanExporter/
FastAPIInstrumentor setup, same OTEL_EXPORTER_OTLP_ENDPOINT env var,
confirmed present on the running pods). Requests to these services
succeed normally (200 OK, correct response bodies, logged in real
time), but no spans for either service ever appear in Tempo, under
any trace ID — neither their own root traces nor as children of an
api-gateway-initiated trace.

**Root cause (suspected, not confirmed):** OpenTelemetry's
BatchSpanProcessor silently swallows exporter failures by default —
it does not raise or log through the application's own logging setup.
Extensive live log monitoring during real requests to auth-service
showed zero OTel-related output of any kind, which is consistent with
a silent gRPC export failure specific to that service's environment,
not with a code or configuration difference (none was found after
line-by-line comparison against api-gateway).

**Ruled out:**
- Stale pod / old image (confirmed fresh env vars and recent deploys)
- Missing OTEL_EXPORTER_OTLP_ENDPOINT (confirmed present)
- Linkerd stripping the traceparent header in transit (a manually
  injected header was echoed correctly through the mesh to a test
  service)
- Request not reaching the service (confirmed via live logs during
  the exact test window)

**Next step, if revisited:** Enable OTel SDK diagnostic logging
(`opentelemetry.sdk._logs`) or wrap the OTLPSpanExporter's export
call to explicitly catch and print gRPC status codes, since the
default configuration provides no visibility into why the export
is failing.
