# Runbook: Disk Full (Node Disk Pressure)

## Detection
Kubernetes marks a node with a `DiskPressure` condition when available
disk drops below its eviction threshold; pods on that node begin
getting evicted. Alert fires on the `DiskPressure` node condition or on
scheduled pods failing with `Evicted` status.

## Diagnosis
1. Confirm which node and how bad:
    kubectl get nodes
    kubectl describe node <node> | grep -A5 Conditions
2. Check what's actually consuming space — usually container images and
   logs, not app data, since these are stateless services with no
   persistent volumes:
    kubectl debug node/<node> -it --image=busybox -- df -h /host
3. Check for evicted pods as confirmation of impact:
    kubectl get pods -A | grep Evicted

## Mitigation
- Immediate relief: clean up unused images on the node (kubelet garbage
  collection usually handles this automatically, but can be forced):
    kubectl debug node/<node> -it --image=busybox --       chroot /host crictl rmi --prune
- If the node is an EKS managed node, the more durable option is
  replacing it rather than manually clearing space:
    kubectl cordon <node>
    kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
  (the ASG will replace it with a fresh node)

## Resolution
- DiskPressure condition clears on `kubectl describe node`.
- No new evictions after cleanup/drain.

## Escalation
- If disk fills up repeatedly rather than as a one-off, this is a
  capacity-planning problem, not an incident — increase node disk size
  or count in Terraform rather than repeatedly firefighting it.
