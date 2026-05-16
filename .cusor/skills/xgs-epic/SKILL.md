---
name: xgs-epic
description: Plan and analyze an Epic. Explore codebase, assess risks, create implementation overview.
---

# Epic Planning

**Command:** `/epic <JIRA-ID>`

**Purpose:** Creates implementation overview for an Epic by analyzing requirements and codebase.

---

## Process

1. **Fetch Epic**
   - Read JIRA Epic: summary, description, linked Stories
   - Identify design document (Confluence link or Epic description)

2. **Explore Codebase**
   - Identify affected modules
   - Find reference implementations
   - Note existing patterns

3. **Risk Assessment**
   - Evaluate each dimension (1-3 scale)
   - Calculate total risk score

4. **Present Overview**
   - Show findings and risks
   - Propose implementation approach
   - **⚠️ CHECKPOINT:** Wait for approval

5. **Create Stories** (if needed)
   - Split Epic into Stories
   - Add to JIRA (with approval)

---

## Risk Assessment

| Dimension | Low (1) | Medium (2) | High (3) |
|-----------|---------|------------|----------|
| Scope | ≤3 files | 4-10 files | 10+ files |
| Dependencies | All exist | Some needed | Major groundwork |
| Thread Safety | Single thread | Some shared | Complex locking |
| Testing | Unit only | Device needed | E2E required |
| Reversibility | Easy rollback | Moderate | One-way door |

**Risk Levels:**
- 5-7: Low → Standard implementation
- 8-10: Medium → Extra review needed
- 11-15: High → Spike/POC first

---

## Output

```
epic/<EPIC-ID>/
└── <EPIC-ID>_OVERVIEW.md
```

---

## Template

**File name**: `EPIC Analysis for <JIRA-ID> <Title>.md`

```markdown
# EPIC Analysis for <JIRA-ID> <Title>

| Field | Value |
|-------|-------|
| Target Release | Hank-x.x |
| EPIC | <JIRA-ID> |
| Document status | DRAFT / REVIEWED |
| Authors | |
| Key Reviewers | |

## Scope & Requirement

See requirement in [<JIRA-ID>](https://jira.vecima.com/browse/<JIRA-ID>)

<Brief summary of what this EPIC covers>

## Assumptions

<List assumptions made for this design>

## Overview of solution

<High-level solution description>

## Open points

<Any unresolved questions or decisions>

## Detailed Designs

### Solution & Implementation

<Technical details, data models, code snippets>

### Test case list - DoD of this EPIC

| Item | Test case description | Comments |
|------|----------------------|----------|
| 1 | | |
| 2 | | |

### List function areas, which might be modified

- xpon-apps/<module>
- netconf-polt/<module>
- xpon-libs/<module>

## Impact to VPON Manager

<If applicable, describe impact to vPON Manager>
```

---

## Checkpoints

| Step | Checkpoint |
|------|------------|
| After analysis | Confirm findings before planning |
| Before JIRA changes | Approve Story creation |
