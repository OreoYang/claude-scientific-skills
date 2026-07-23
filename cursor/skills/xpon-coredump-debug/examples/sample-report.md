# Coredump Analysis Report

## Summary

`bcmolt_netconf_server` (PID 4521) crashed with SIGSEGV in `omci_svc_state_up_sequence_end_event_start` at `omci_svc_onu.c:3587` while dereferencing a freed `onu_context` pointer. Root cause is a use-after-free race: ONU deactivation freed the context while an in-flight async activation callback still held the stale pointer.

## Environment

| Item | Value |
|------|-------|
| Build | xpon-olt-bundle 2.4.1-rc3 |
| Platform | EXS1610 (exs1610) |
| PID | 4521 |
| Crash thread | 3 |
| Crash time | 2026-07-05T14:32:18Z |
| Signal | SIGSEGV (signal 11) |
| Fault address | 0x00007f8a4c0013e8 |

## Complete Backtrace

```
#0  omci_svc_state_up_sequence_end_event_start (onu_context=0x7f8a4c0013e8)
     at omci_svc_onu.c:3587
#1  0x00007f8a4b12a440 in omci_svc_sm_event_handler () at omci_svc_sm.c:892
#2  0x00007f8a4b08c1a0 in taskman_worker () at taskman.c:214
...
```

## Root Cause

### Crash Location

`omci_svc_onu.c:3587` — read of `onu_context->onu_id` after context was freed.

```c
// omci_svc_onu.c:3587
if (onu_context->onu_id != expected_id)
```

### Why the Pointer is Invalid

`onu_context` was allocated during ONU activation. Deactivation on another thread called `omci_svc_onu_context_free()` before this async callback ran. Address `0x...13e8` is a small offset into freed heap memory (classic UAF pattern).

### Race Condition Trigger

1. ONU activate starts; `onu_context` allocated, async OMCI sequence scheduled
2. Operator deactivates ONU; context freed, entry removed from hash
3. Async sequence completion fires on taskman worker thread
4. Callback uses stale `onu_context` → SIGSEGV

### Call Chain Summary

`taskman_worker` → `omci_svc_sm_event_handler` → `omci_svc_state_up_sequence_end_event_start` (crash)

## Fix Applied

**File**: `netconf-polt/onu_mgmt/omci_svc_onu.c`

Hold a ref-count or validate context still exists in ONU table before dereference in async completion path; cancel pending async work on deactivation.

```c
// After: lookup onu_context by onu_id under lock; return early if not found
```

## Reproduction Conditions

- Rapid ONU deactivate immediately after activate (or during OMCI up-sequence)
- Multi-threaded taskman + OMCI state machine under load

## Severity / Impact

- **High** for affected ONU: `netconf-polt` restarts via systemd
- Brief NETCONF/OMCI service disruption on that PON port
- No data corruption observed beyond process exit
