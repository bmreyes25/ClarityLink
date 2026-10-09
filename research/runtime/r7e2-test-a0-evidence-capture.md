# R7E2 A0 evidence capture templates (ECC)

## A0-R (Tier 1; separately authorized)

```text
Authorization reference:
Date/time/timezone:
Operator:
Vehicle stationary: YES/NO
Parking state directly observed:
Power mode directly observed (exact display/control label; do not infer from ADB):
Center display fully booted: YES/NO
Cluster normal: YES/NO
Unexpected warnings: NONE / describe and STOP
Intended target count from adb devices: 1 / STOP
Target identity: REDACTED; local record reference only:
Target state: device / otherwise STOP
Shell id output (UID/GID/groups; sanitize):
Android release / SDK / ABI:
pwd:
/data metadata:
/data/local metadata:
/data/local/tmp metadata or ABSENT:
/proc/mounts relevant /data line:
/proc/self/status relevant identity:
SELinux read result: value / absent / denied / command unavailable
Command exit statuses and sanitized output references:
Stock center UI/cluster/warning/audio observation:
Unexpected mutation: NONE / describe, STOP
Result: COMPLETE / PARTIAL / STOP
No target writes / no chmod / no push / no execution: confirm
Reviewer and disposition:
```

## A0-W (Tier 2; separately authorized only after A0-R)

```text
Authorization reference:
Date/time/timezone:
Approved A0-R result reference:
Exact destination from approved A0-R:
Unique approved nonce:
Exact marker path:
Expected payload byte count/hash/content:
Pre-create absence verified:
Create result:
Observed bytes/hash/content:
Observed owner/mode:
Exact deletion result:
Absence verification:
Unexpected mutation: NONE / describe and STOP
Stock center UI/cluster/warning/audio observation:
Rollback complete: YES/NO
Commands and exit statuses:
Result: COMPLETE / PARTIAL / STOP
No chmod / no execution / no wildcard / no unrelated path touched: confirm
Reviewer and disposition:
```

Never place VIN, serial, IP, or unredacted device identity in Git. Keep raw host captures access-controlled; commit only sanitized findings.
