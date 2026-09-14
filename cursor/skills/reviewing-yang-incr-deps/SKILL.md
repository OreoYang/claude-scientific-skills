---
name: reviewing-yang-incr-deps
description: >-
  Use when reviewing newly added or changed YANG when, must, leafref, or unique
  under incremental sysrepo/libyang validation, to detect a classification that
  would skip a constraint an edit can actually break (missed validation).
---

# New YANG vs incremental miss

**Job:** for each new/changed `when` / `must` / require-instance leafref / `unique`, decide whether incremental apply can **skip a node whose constraint the edit can violate**.

Source of truth: `lyd_val_dep_classify_expr()` (`libyang` `src/validation_deps.c`; pin sysrepo 3.7.11 + libyang 3.9.13, `SR_VALIDATE_INCREMENTAL=1`). LCA intuition: wiki **§7 Schema LCA** on [Incremental YANG validation Design](https://vecima.atlassian.net/wiki/spaces/~Oreo.Yang/pages/266863799/Incremental+YANG+validation+Design+ConfD-style+incremental#7.-Schema-LCA).

## When it is a miss

Apply has two buckets:

| Bucket | Tool class | What apply skips |
|--------|------------|------------------|
| skip-extra | LOCAL, LIST-SCOPE | other `list` / `leaf-list` instances **not** under the dirty root |
| extra | BOUNDED, UNBOUNDED | nothing for that schema node when atoms are hit (`creation_safe` skips extra on **create** only) |

Dirty root = **outermost** list instance that contains the changed node (not `unit`, not “this row”).

A **miss** is: tool class is skip-extra, **and** the expression can be broken by an edit whose dirty root does **not** contain the constrained node.

Skip does not hide XML from XPath. It only refuses to **re-run** constraints hanging on skipped instances.

## Classify (same order as C)

1. No expr, atom walk fails, `//`, `*`, `pfx:*`, `node()`, variables, non-simple axis, unknown function → UNBOUNDED.
2. Leading `/` or `deref()` → `current()`/`deref()` + key predicates → BOUNDED; else UNBOUNDED.
3. Relative. Schema atoms vs context: no LCA (left the top-level node) → step 2.
4. Else LIST-SCOPE if the climb from an atom to the LCA passes a `list`/`leaf-list` that is **not** the LCA; otherwise LOCAL.
5. `unique` is always LIST-SCOPE. Rechecked on the parent among **all** sibling rows — not a skip miss.

Schema LCA cannot tell “this row’s `../leaf`” from “every row of the same list” (`../../list/key`, `count(../…)`, `[name=current()]`). That is LOCAL in the report. Whether it is a **miss** depends on the next section, not on renaming the class.

## Hole vs covered (only this matters)

Let **O** = outermost `list` that contains the context node.

| Pattern | Tool | Miss? |
|---------|------|-------|
| `../leaf` on the **same row** (`current() != ../from-interface`) | LOCAL | No |
| `..` exits an **inner** list, nametest re-enters it; still inside **O** (`../../component/name` under `onu`/`interface`) | LOCAL | **No** — dirty root is O, sibling inner rows are walked |
| `..` exits **O**, nametest re-enters **O** (sibling rows of the outermost list) | LOCAL | **Yes** — edit of sibling O skips this instance |
| Relative path that actually leaves O / the top-level instance, but still LOCAL or LIST-SCOPE | skip-extra | **Yes** — extra never runs |
| Absolute / `deref()` | BOUNDED or UNBOUNDED | No skip-miss (extra). Create-only miss if `creation_safe` is wrong on a `must`/`when` that new data can fail |

Do **not** flag inner-list re-entry as a validation bug. Do **not** “fix” it with an absolute path (that moves the rule to extra).

Do **flag** outermost-list re-entry: the classifier will skip-extra, apply will skip other O instances, and those edits can violate the rule. Options: nest under a wider list, or accept extra (absolute + key → BOUNDED).

## Output (new/changed nodes only)

```
node | construct | tool class | miss? | why
```

`miss?` is **yes** only for a skip-extra rule whose data reach includes a list instance apply would skip. Omit clean same-row LOCAL.

Golden A–E: [examples.md](examples.md)
