# Improve Loop

Three checks that make the output better each time, run by the agent itself —
no API, no IMAP login. Thresholds come from what usually separates working
cold outreach from noise; adjust them if the user has their own numbers.

| Loop | When | Fixes |
|---|---|---|
| 1. Quality gate | After writing the files, before leads | Vague product/ICP, broken email rules |
| 2. Lead scoring | After finding leads, before drafting | Off-target leads, loose ICP |
| 3. Results review | After the user has sent ≥ 20 emails | Low replies, wrong-person replies |

Every loop ends by appending what it learned to `learnings.md` (format at the
bottom). Read that file at the start of any later run for the same company —
it's how the system gets better across runs instead of repeating mistakes.

---

## Loop 1 — Quality gate

**Mechanical checks.** If you can run Python, run
`python3 scripts/check_files.py outreach/{slug}` (path relative to this
skill's folder for the script). It checks word limits, leftover placeholders,
banned filler phrases, subject length and the `leads.csv` columns, and prints
every failure. If you can't run code, do the same checks by hand — count the
words of each email body, don't estimate.

**Judgement checks.** Score each file 1 point per criterion met.

`product.md` (pass at 5/6):
1. Core offering is clear in the first paragraph
2. Deliverables are specific items, not generic phrases
3. At least one concrete proof point (client, number, or outcome) — real, from the brief
4. Differentiators are specific
5. Deal size or target client size is stated (or explicitly marked unknown)
6. Clear statement of who they do not work with

`target.md` (pass at 5/6):
1. At least 2 clearly distinct verticals
2. Each vertical has specific job titles (not "decision maker")
3. Each vertical has keywords you could actually search for
4. Disqualifiers are specific enough to reject a real company
5. Geography is stated
6. "Perfect lead" reads like a real person, not a filter list

`email-sequences.md` (pass at 5/6):
1. Every Email 1 opens with something about *them*, not the sender
2. One pain point per email, stated as an observation
3. Proof point is real (traceable to the brief)
4. Exactly one soft CTA per email
5. Would make sense to the buyer if the company name were hidden — i.e. specific, not template-shaped
6. Opt-out line present

**Fix.** Rewrite only what failed — keep everything else word-for-word —
then re-check. Stop after 2 rounds; if something still fails, it usually
means a fact is missing (e.g. no proof point exists), so tell the user what's
missing rather than inventing it.

## Loop 2 — Lead scoring

Score every lead in `leads.csv` against `target.md`, 1–10:

- **9–10** perfect: right vertical, right title, live buying signal
- **7–8** strong: right vertical and title, weaker or no signal
- **5–6** borderline: one of vertical/title is a stretch
- **1–4** reject: hits a disqualifier, wrong role, or stale info

Add `score` and `score_reason` columns. Drop rejects from the drafts (keep
them in a `rejected-leads.csv` so they aren't re-found next run). Sort the
rest by score.

**If more than 30% were rejected**, the ICP is too loose to search with.
Add specificity to `target.md` that would have excluded those rejects (add
disqualifiers, narrow titles or company stage — don't delete verticals),
show the user the change, then search again to replace the rejects. Do this
at most once per run.

## Loop 3 — Results review

Run when the user comes back with results, e.g. "review my outreach",
"I sent 40 emails and got 2 replies", or on a schedule (see below).

**Get the data — in this order of preference:**
1. A mail tool the user already connected to you (e.g. a Gmail/Outlook
   connector) — read replies to the threads in `outreach-drafts.md`. Read-only.
2. The user pastes the replies, or exports them.
3. The user just gives numbers (sent, replies, and roughly what kinds).

**Classify each reply:** `interested`, `not_now`, `wrong_person`,
`unsubscribe`, `bounce`, `other`. Update `tracking.csv`
(`name,company,email,sent_date,status,reply_class,reply_summary,next_action`)
and give the user the next action for every `interested` and `not_now`.
Treat `unsubscribe` as permanent — mark it so nobody re-contacts that person.

**Compute:** reply rate = replies ÷ sent; wrong-person rate = wrong_person ÷
replies; bounce rate = bounces ÷ sent. Ignore rates below 20 sends — too
noisy to act on; just log them.

**Act on what the numbers say:**

| Signal | Likely cause | Change |
|---|---|---|
| Reply rate < 3% (≥ 20 sent) | Copy or hooks | Rewrite `email-sequences.md`: sharper hook, one pain point, shorter. Use what the `not_now` / `wrong_person` replies reveal. |
| Wrong-person > 30% of replies | ICP titles | Refine titles/seniority in `target.md`; re-score current leads |
| Bounce > 5% | Email guesses | Stop sending to `guess` emails; prefer `published` / `pattern-confirmed` next run |
| Many `not_now` | Timing | Lean harder on buying signals in Loop 2 (signal 1–3 only) |
| Interested ≥ 2 | Working | Note which vertical and hook worked; find more leads like those |

**Before changing any file**, show the user a short before/after of what you
changed and why, and get a yes. Exception: if the user said to run
unattended, apply it and list the changes in the summary.

## learnings.md

Append, never overwrite:

```
## {date} — {loop name}
- Data: {e.g. 42 sent, 3 replies (2 interested, 1 wrong_person), 1 bounce}
- Changed: {file — what changed, one line each, or "nothing"}
- Learned: {one line, e.g. "Ops managers reply; CTOs forward to ops"}
```

On the next run for this company, read it first and apply it: search the
verticals and titles that worked, skip the ones that didn't, reuse the hook
types that got replies.

## Running it on a schedule

The loop works best weekly while a campaign is live. Use whatever the agent
has — don't build a scheduler:

- **Claude Code / Claude desktop:** a weekly scheduled task with the prompt
  "review my outreach results for {slug}"
- **Hermes Agent:** a cron job with the same prompt
- **Anything else:** the user asks "review my outreach" each week
