---
name: xgs-bug
description: Analyze and fix a Bug. Root cause analysis, fix implementation, JIRA update.
---

# Bug Fix

**Command:** `/bug <JIRA-ID>`

**Purpose:** Analyzes bug, identifies root cause, implements minimal fix.

---

## Process

1. **Setup**
   - Read JIRA bug: description, comments, attachments
   - Download attachments to `bug/<JIRA-ID>/attachments/`

2. **Analyze**
   - Extract reproduction steps
   - Identify error logs/symptoms
   - Trace code to find root cause

3. **Document RCA**
   - Create `<JIRA-ID>_BUG_ANALYSIS.md`
   - **⚠️ CHECKPOINT:** Present root cause, wait for approval

4. **Update JIRA**
   - Add RCA comment (concise format)

5. **Implement Fix**
   - Create branch `frzhou/<JIRA-ID>`
   - Make minimal code changes
   - Compile: `bitbake xpon-olt-bundle`

6. **Release Note**
   - Update JIRA field `Release Note Information` (`customfield_14700`) with a 1-2 sentence summary for PLM/release documentation
   - Format: what was fixed + workaround if applicable
   - Use `jira_update_issue` with `fields: {"customfield_14700": "<text>"}`

7. **Summary**
   - List files changed
   - Suggest commit message with root cause

---

## RCA Comment Format (JIRA)

```
h2. Root Cause Analysis

h3. Problem
<1-3 sentences>

h3. Fix
<1-2 sentences>

h3. Files Changed
* {{path/to/file.c}}
```

---

## Output

```
bug/<JIRA-ID>/
├── attachments/               # From JIRA
└── <JIRA-ID>_BUG_ANALYSIS.md  # RCA document
```

---

## Templates

### Bug Analysis Template

```markdown
# <JIRA-ID> Bug Analysis

**Date**: <today>
**Priority**: <from JIRA>
**Reporter**: <from JIRA>

## Problem Summary
<from JIRA description>

## Reproduction Steps
1. ...
2. ...
3. ...

## Error Logs
```
<relevant log snippets>
```

## Root Cause
<your analysis - explain WHY the bug occurs>

## Proposed Fix
- **File**: `<file>:<line>`
- **Strategy**: <brief description>
- **Risk**: Low/Medium/High

## Affected Components
- [ ] xpon-apps
- [ ] netconf-polt
- [ ] xpon-libs
- [ ] xpon-protos
```

### Commit Message Template

```
<JIRA-ID>: <Brief description of fix>

<Explanation of bug and fix>
<Why this fix is correct>

Root cause: <one line summary>
```

**Example:**
```
XGS-12345: Fix memory leak in DHCP session cleanup

When VLAN subinterface is deleted, session cleanup causes
double-free because anti-spoofing also tries to free entry.

Changed to use IP_DEL_FROM_HW_ONLY flag.

Root cause: Session ownership ambiguity between tree and VSI.
```

---

## Checkpoints

| Step | Checkpoint |
|------|------------|
| After RCA | Confirm root cause before fix |
| Before commit | Review fix and message |
| Release Note | Update `customfield_14700` in JIRA |

---

## Common Bug Patterns

| Category | Investigation Focus |
|----------|---------------------|
| Memory | malloc/free pairs, double-free |
| Race condition | Thread safety, locking |
| NULL pointer | Validation before use |
| Resource leak | FD/socket close |
