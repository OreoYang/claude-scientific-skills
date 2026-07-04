# Netconf-polt mutex rule

Developer mandate for lock contention and deadlock avoidance in `netconf-polt` / `bbf-xpon`.

**Code:** `bbf-xpon-internal.h` (L1–L7 ladder), `bbf-xpon-channel-termination.c`, `bbf-xpon-onus-onu.c`, `ipc-metrics-mgr-internal.h`

## Lock inventory (L1–L7)

| L | Lock | API | Protects |
|---|------|-----|----------|
| L1 | `nc_config_lock` | config path | Transactions; brief snapshots (~100 µs) |
| L2 | `xpon_obj_config_lock` | inside `xpon_object_*` only | `redis_dict[]` name hash |
| L3 | `xpon_cterm_config_lock` | `xpon_cterm_list_lock()` | `cterm_list`, `cterm_by_id_array` |
| L4 | `onu_tmpl_config_lock` | `XPON_ONU_TMPL_CONFIG_GUARD()` | `onus_rb` instance index |
| L5 | `onu->onu_inst_config_rwlock` | `xpon_onus_onu_lookup_*lock` | template ONU overlay |
| L6 | `vani_per_pon_runtime_lock[b]` | `XPON_VANI_RUNTIME_GUARD` | `v_ani_list`, `v_ani_array`, `discovered_onu_list`, CT runtime aux |
| L7 | `ani_runtime_rwlock` | `ani_runtime_rdlock()` | `ani_list`, `xpon_ani` PM |

**Traps:** L2 ≠ L3. `vani_per_pon_runtime_lock[32]` = UNASSIGNED. `hardware_list` — L1 snapshot only.

## Domain data source (no cross-layer L2 read)

Hold lock → read **that layer's list**. No `xpon_object_get*` from L3/L6/L7 (`dictFind`, no lock).

| Lock | Read | Not |
|------|------|-----|
| L3 | `cterm_list`, `cterm_by_id_array` | L2 hash |
| L6 | `v_ani_list[b]`, `v_ani_array` | `xpon_object_get*` |
| L7 | `ani_list` | `xpon_object_get_by_key_and_type` |
| L1 | L2 hash OK (brief, config) | — |

Snapshot = pointer lifetime (F-8), not wrong source. Oper-get: same domain list for Named/Unnamed.

## Lock order

`L1 → L2 → L3 → L4 → L5 → L6 → L7`. `lookup_*` releases L4 before return (caller holds L5).

| ID | Rule |
|----|------|
| O-1 | `lookup_*` releases `onu_tmpl_config_lock` before return |
| O-2 | Never `lookup_*` under L6 or L1 |
| O-3 | Avoid `lookup_*` under L1 unless short snap, no 3rd lock |
| O-4 | Delete: `RB_REMOVE` → `wrlock` → teardown |
| O-5 | Rebucket: two L6, lower index first |
| O-6 | L6 recursive; L5 **not** recursive |
| O-7 | L1 **not** recursive |

**Allowed:** L3→L6 (CT GET). **Forbidden:** L3→L1, L6→L3, 3+ locks (F-6).

## Execution planes (sysrepo)

| Plane | Rule |
|-------|------|
| **OPR-1** Oper-push | No L1–L7 during `sr_set_item*` / `sr_apply_changes`. Phase 1: snap → unlock; Phase 2: sysrepo |
| **OPR-2** Oper-get | ≤2 locks, short snap. No BAL, no oper-push, no `lookup_*` under L6 |
| **CFG-1** Config | L1 (+L5) may use running `sr_get_*`. No oper-push under L1 |
| **ASYNC-1** Indication/metrics | Phase 1 snap → Phase 2 BAL/event/oper-push |

## Golden rules

1. ≤2 locks (dual L6 rebucket excepted).
2. No slow I/O under lock (BAL, sleep, protobuf, operational sysrepo).
3. Two-phase snapshot: copy under lock, work outside.

## Reduce locks

| Instead of | Do |
|------------|-----|
| Pointer after unlock | Snapshot scalars/strings |
| L1 + foreach + BAL | Phase 1 snap; Phase 2 BAL |
| `foreach` + BAL in cb | Cb = snap only |
| Global v-ANI scan | Per-bucket `XPON_VANI_RUNTIME_GUARD(b)` loop |
| `lookup_*` under L6 | Snap under L6, unlock, `lookup_rdlock` |
| L6/L7 oper-get via L2 | Walk `v_ani_list` / `ani_list` (F-15) |

## Blacklist

| ID | Pattern |
|----|---------|
| F-5 | `lookup_*` under L6 |
| F-6 | 3+ locks |
| F-7 | BAL under L1/L6 |
| F-8 | Pointer use after unlock without snap |
| F-10 | BAL in `xpon_onus_onu_foreach` cb |
| F-13 | Operational sysrepo under L1–L7 |
| F-14 | BAL in oper-get under L3/L6 |
| F-15 | L3/L6/L7 uses L2 `xpon_object_get*` not domain `*_list` |

## Review checklist

1. Lock maps to L1–L7? ≤2 locks? Order OK?
2. `lookup_*` paired with `xpon_onus_onu_rwunlock` on all paths?
3. Execution plane: OPR-1/2, CFG-1, ASYNC-1?
4. Oper-push only after GUARDs released?
5. Two-phase snap on non-config threads?
6. `pon_ni == 255` → `xpon_vani_runtime_lock_bucket()` / `xpon_v_ani_bucket()`?
7. Domain list not L2 hash (F-15)?

## Verify grep

```bash
rg 'pthread_rwlock_(rd|wr)lock\(&.*->onu_inst_config_rwlock\)' netconf-polt --glob '!**/bbf-xpon-onus-onu.c'
rg 'onu_config_lock' netconf-polt/netconf_server/modules/bbf-xpon
rg 'xpon_object_get|xpon_v_ani_get_by_name' netconf-polt/netconf_server/modules/bbf-xpon/bbf-xpon-v-ani.c bbf-xpon-ani.c
```
