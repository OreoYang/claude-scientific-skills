---
name: standup-meeting
description: >-
  Generate short spoken-English standup updates (3–5 sentences, simple words).
  Use when the user asks for standup, daily update, scrum update, status report,
  or a brief English summary of their work.
---

# Standup Meeting

Turn the user's work notes (Chinese or English) into a short standup script they can say out loud in a team meeting.

## Output rules

1. **Length**: 3–5 sentences total. Never more than 5.
2. **Tone**: Spoken English — sounds natural when read aloud, not like a formal report.
3. **Vocabulary**: Simple, everyday words. Avoid jargon unless the user used it (e.g. JIRA ticket ID, feature name).
4. **Tense**: Past for done work, present/future for today and next steps.
5. **Structure** (implicit — do not label sections unless the user asks):
   - What you finished or worked on recently
   - What you are doing today / next
   - Blockers or help needed (one short line, or skip if none)
6. **No filler**: Skip greetings, sign-offs, and "I hope everyone is doing well."
7. **Deliver only the script** — no Chinese translation, no explanation, unless the user asks.

## Word choices (keep it simple)

| Prefer | Avoid |
|--------|-------|
| worked on, fixed, finished, tested | implemented, leveraged, facilitated |
| bug, issue, change | regression, remediation |
| still waiting on, blocked by | impeded by, contingent upon |
| I'll look at, I'll continue | I shall proceed to investigate |
| team / someone | stakeholder, cross-functional partner |

## Workflow

1. Read what the user gives: tasks, tickets, git work, or rough notes.
2. Pick the 1–2 most important items for "recent" and 1–2 for "today."
3. Merge small tasks into one line (e.g. "code review and small fixes").
4. Write 3–5 sentences in first person ("I").
5. If info is missing, use neutral placeholders only when necessary — prefer asking one short question instead.

## Templates

**Default (no blockers):**
> Yesterday I [past action]. Today I'll [today's plan]. [Optional: one line on context or priority.]

**With blocker:**
> Yesterday I [past action]. Today I plan to [today's plan]. I'm blocked on [issue] — [what you need, if any].

**Light day / admin:**
> Yesterday I [meetings / leave / admin]. Today I'll get back to [main task].

## Examples

**Input (notes):**
- 昨天修了 OMCI 超时 bug，提了 CR
- 今天继续 XGS-11109 mutex 文档
- UKG 假期还没更新

**Output:**
> Yesterday I fixed an OMCI timeout bug and opened a code review. Today I'll keep working on the XGS-11109 mutex documentation. I also need to update my leave balance in UKG when I get a chance.

---

**Input (notes):**
- finished PR feedback for netconf-polt
- today: bitbake compile and test on lab OLT
- waiting for BAL SDK answer from Hank

**Output:**
> Yesterday I addressed the review comments on the netconf-polt PR. Today I'll run a bitbake build and test on the lab OLT. I'm still waiting on Hank for a BAL SDK question, so that part is on hold.

---

**Input (notes):**
- 下周一休假
- 本周在做 onu_mgmt refactor

**Output:**
> This week I've been working on the onu_mgmt refactor. I'll be out next Monday and will update my leave in UKG before then.

## When the user gives almost nothing

Ask one short question:

> What did you work on yesterday, and what's the plan for today?

Then generate the standup from their answer.
