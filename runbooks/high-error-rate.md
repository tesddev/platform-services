# Runbook: High Error Rate

## Detection
Alert fires when a service's 5xx rate (via Linkerd golden metrics) exceeds
a threshold — e.g. success rate < 95% sustained for 2+ minutes.
Confirm in Grafana: the success-rate panel on the platform dashboard will
show which deployment dropped below the line.

## Diagnosis
1. Identify the affected service from the Grafana panel or alert label.
2. Check recent deploys first — most error spikes correlate with a rollout:
   kubectl get application <service> -n argocd -o jsonpath='{.status.sync.revision}'
   Compare against the last known-good commit SHA.
3. Check pod-level errors directly:
   kubectl logs -n platform deployment/<service> --tail=50
4. Check if it's isolated to one service or cascading (gateway errors often
   mean an upstream dependency, e.g. auth-service, is the real cause):
   linkerd viz stat deployment -n platform

## Mitigation
- If tied to a recent deploy: roll back immediately via ArgoCD rather than
  debugging forward under pressure.
    argocd app rollback <service> <previous-revision>
  (or, without the ArgoCD CLI, revert the commit in Git — ArgoCD's
  auto-sync will pick it up within its sync interval)
- If it's a dependency failure (e.g. auth-service down, gateway errors as
  a symptom): mitigate the root service, not the symptom service.

## Resolution
- Confirm success rate returns to baseline in Grafana.
- Root-cause the actual code/config change once traffic is stable —
  do not investigate root cause while still in the degraded state.

## Escalation
- If rollback doesn't resolve it within 10 minutes, or the cause is
  outside the app layer (cluster/node issue), escalate — open a GitHub
  issue tagged `incident` with the Grafana screenshot and timeline so far.
