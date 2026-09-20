# Runbook: Service Unavailable (Pod Crash / CrashLoopBackOff)

## Detection
Alert fires when a deployment has 0 available replicas, or a pod enters
CrashLoopBackOff. Grafana request-rate panel for that service drops to
zero while others stay flat — that's the visual tell before any alert
even fires.

## Diagnosis
1. Confirm pod state:
   kubectl get pods -n platform -l app=<service>
2. Get the reason for the crash:
   kubectl describe pod -n platform <pod-name>
   (check Events at the bottom — OOMKilled, failed probe, image pull
   error, and a code-level crash all show differently here)
3. Get the actual crash output:
   kubectl logs -n platform <pod-name> --previous
   (--previous is essential — the current container has no logs yet if
   it just crashed and restarted)

## Mitigation
- OOMKilled: this is a resource limit problem, not a code problem in the
  short term — bump `resources.limits.memory` in the Helm values and
  push; ArgoCD will pick it up.
- Bad image/crash on startup: roll back to the last known-good tag the
  same way as the high-error-rate runbook.
- If only some replicas are affected: the healthy replicas are still
  serving traffic via the Service — this is often not a user-facing
  outage yet, which changes urgency.

## Resolution
- All replicas Running and Ready:
    kubectl get pods -n platform -l app=<service>
- Confirm traffic resumes in Grafana.

## Escalation
- If pods won't stay up after a rollback (rules out the last deploy as
  the cause), check node-level health next — the problem may not be the
  app at all:
    kubectl get nodes
    kubectl describe node <node>
