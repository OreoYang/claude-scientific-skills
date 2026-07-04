---
name: xgs-story
description: Implement a Story or Task with Epic context.
---

# Story Implementation

**Command:** `/story <JIRA-ID>`

---

## Process

1. Create folder `story/<JIRA-ID>/`
2. Gather Story context (JIRA ticket, linked issues, attachments)
3. Gather Epic context (parent Epic, design docs, Confluence pages)
4. Read relevant code and identify changes needed
5. Present analysis and wait for approval
6. Create branch `frzhou/<JIRA-ID>` if needed
7. Implement and compile
8. Present summary with commit message

---

## Context Gathering

| Source | What to Find |
|--------|--------------|
| Story JIRA | Description, acceptance criteria, links, attachments |
| Epic JIRA | Description, links, related Confluence pages |
| Confluence | Search for Epic Analysis page (semantic match on Epic ID) |

---

## Checkpoints

| Before | Ask |
|--------|-----|
| Coding | Confirm approach |
| Branch creation | Approve branch name |
| Commit | Review changes |

---

## Output

Location: `story/<JIRA-ID>/`

| File | Content |
|------|---------|
| `*_FINDINGS.md` | Analysis |
| `*_PLAN.md` | Plan (if complex) |
