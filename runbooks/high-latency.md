# Runbook: High Latency (P99 > 2s)

## Detection
Alert fires when the P99 latency panel (Linkerd `response_latency_ms`
histogram, per deployment) exceeds 2000ms sustained for 5+ minutes.

## Diagnosis
1. Identify which service is slow — check each service's P99 individually
   rather than only the gateway, since the gateway's latency is the sum
   of its own work plus whatever it calls:
    linkerd viz stat deployment -n platform
2. Rule out resource starvation first — it's the most common cause and
   the fastest to check:
    kubectl top pods -n platform
   If CPU is pinned near its limit, that's very likely your answer.
3. If resources look fine, check for a downstream dependency being slow
   rather than the service itself (gateway slow because auth-service is
   slow is a different fix than gateway itself being slow):
    linkerd viz stat deployment -n platform --to auth-service
4. Check for a recent deploy correlating with the latency change, same
   as the error-rate runbook.

## Mitigation
- Resource-starved: scale replicas or raise CPU limits — whichever is
  faster to ship safely given the time of day.
    kubectl scale deployment/<service> -n platform --replicas=<n>
- Downstream dependency slow: mitigate at the dependency, not the
  symptom service.
- Recent deploy: roll back.

## Resolution
- P99 back under threshold, sustained for 10+ minutes (not just a single
  good reading — latency issues often bounce before actually resolving).

## Escalation
- If latency is uniformly elevated across all three services rather than
  one, suspect the node or network layer, not the app:
    kubectl get nodes -o wide
    kubectl top nodes
