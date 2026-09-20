# Postmortem: notification-service Unavailable (Drill)

**Date:** 2026-09-20
**Duration:** ~6 minutes (17:07:00 – 17:13:00 UTC), notification delivery ~10 minutes
**Severity:** Drill / simulated — no real user impact
**Status:** Resolved

## Summary
notification-service was manually scaled to 0 replicas to simulate a pod
outage as part of a scheduled incident response drill. The configured
Grafana alert correctly detected the outage via a "no data" condition and
notified #incidents in Slack. The on-call engineer followed the
`service-unavailable` runbook and restored the service. A notable gap
was found between actual recovery and the resolved notification landing.

## Timeline (UTC)
- **~17:06:15** — `kubectl scale deployment/notification-service --replicas=0`
  run, simulating the outage
- **17:06:30** — Alert rule enters Pending state (first evaluation cycle
  to observe the metric gone)
- **17:07:00** — Alert fires (`Alerting (Nodata)`) after the configured
  30s pending duration; Slack notification delivered to #incidents
- **17:07:00–17:12:30** — Engineer acknowledges alert, opens
  `runbooks/service-unavailable.md`, confirms pod state via
  `kubectl get pods -n platform -l app=notification-service`, runs
  mitigation
- **17:12:30** — `kubectl scale deployment/notification-service
  --replicas=1` takes effect; alert enters Recovering as metrics resume
- **17:13:00** — Alert returns to Normal internally in Grafana
- **17:17:00** — Slack resolved notification actually delivered —
  ~4 minutes after the alert had already cleared

## Root Cause
Deliberate: replicas manually set to 0 for drill purposes. In a real
incident, the equivalent root cause would be a pod crash loop, a bad
deploy, or a node-level failure evicting the pod — this drill validated
the detection and response path for all of those, not just the "someone
scaled it to zero" case specifically.

## Impact
None (drill). In a live scenario, requests routed through api-gateway to
notification-service would have received 502s for the outage duration —
the gateway's own error rate would have been the second-order signal,
which is why the high-error-rate runbook cross-references this one.

## Detection
Detection lag was ~30–45 seconds, bounded by the alert rule's `for: 30s`
setting plus one evaluation cycle. This is a deliberate floor, not a
limitation to fix — a shorter window trades faster detection for a
higher risk of false positives on brief network blips.

## Response
Total time from alert firing to actual service recovery was ~6 minutes,
all of it diagnosis-and-manual-fix time. The runbook correctly identified
`kubectl get pods` as the first diagnostic step and
`kubectl scale ... --replicas=1` as the fix, matching what was
documented in advance.

## Notification Delivery Gap (finding)
The resolved notification took ~4 minutes to reach Slack after Grafana's
internal state had already returned to Normal. This means an on-call
engineer relying solely on Slack for status would have believed the
incident was still active for 4 minutes longer than it actually was —
harmless here since the engineer was watching `kubectl` directly, but
in a real incident this delay could cause someone to keep escalating or
keep other people paged unnecessarily after the fix already worked.
Likely cause: Grafana's alertmanager-style notification pipeline batches
or re-evaluates before dispatching resolved messages, rather than
sending instantly on state transition — worth checking the notification
policy's group/repeat interval settings rather than assuming it's fixed
behavior.

## Action Items
- [ ] Investigate the 4-minute resolved-notification delay — check
      Notification Policies → group_wait / group_interval settings for
      the Slack contact point
- [ ] Consider a Grafana alert on api-gateway's error rate as a
      second layer, since gateway errors are the user-facing symptom of
      any downstream service outage, not just notification-service's
- [ ] Evaluate whether 6 minutes of manual response is acceptable for a
      real production SLO, or whether this points toward wanting
      auto-restart/self-healing (ArgoCD's `selfHeal: true` already
      covers config drift — this gap is specifically about a manually
      scaled-down deployment, which self-heal alone won't correct if
      the desired state in Git also says 0)
