---
name: daily-job-matcher
description: Find today's 3 best-fit VP/Director of Marketing jobs paying $250k+ base from the user's LinkedIn, Indeed and Working Nomads alert emails (plus the jobs API when configured), rank them by fit with a preference for Los Angeles, Las Vegas, Denver and remote-US, and tailor the resume to a chosen job. Use when asked for today's job matches, the job digest, or to tailor the resume for a listed job.
---

# Daily job matcher

Preferences live in `profile.yaml`. The parsing and filtering code is in `scripts/jobmatch/`.
The resume is **not** in this repo (it's public); see step 4.

## 1. Collect alert emails (Gmail connector)

For each query in `profile.yaml` → `sources.gmail_alerts`, call `search_threads`.
Then call `get_message` with `messageFormat: PLAIN_TEXT` for every message in each
thread (LinkedIn threads can hold several alerts). Write the messages as a JSON array
of `{id, sender, date, subject, plaintextBody}` to a scratch file, never inside the repo.

If a source returns nothing for 3+ days, say so in the digest (the alert may have been paused).

## 2. Parse and filter

```bash
cd .claude/skills/daily-job-matcher/scripts
python3 -m jobmatch.cli candidates <scratch>/messages.json --seen <state>/seen_jobs.json --out <scratch>/candidates.json
```

The summary on stderr shows what each source yielded and why jobs were rejected.
Kept jobs either pass the $250k base rule or have no posted salary and are flagged
`base unverified`.

If `JSEARCH_API_KEY` is set, also query JSearch for each target title × (United
States, Los Angeles, Las Vegas, Denver, remote), with `date_posted=3days`, and merge
the results before filtering. (The adapter isn't built yet; see the plan's Phase 1.)

## 3. Score and pick 3

For each candidate (fetch the full description from its URL where reachable), score
fit 0–100 against the resume and `profile.yaml` strengths. Record a two-sentence
rationale, top 3 matching strengths, and gaps. For `base unverified` jobs, estimate
base from title, level and company size, and state that it's an estimate.

Final score = 0.70 × fit + 0.15 × comp confidence (posted = 100, estimated ≥ $250k = 50)
+ 0.15 × location (LA/LV/Denver = 100, remote-US = 90, other US = 40).
Pick the top 3, with at most one `base unverified`, and include an LA/LV/Denver role when
one has fit ≥ 75. If fewer than 3 qualify, show fewer and say why. Never pad.

Add the shown jobs to `seen_jobs.json` (`<source>:<source_id>` and the job key).

## 4. Tailor the resume (on request)

Load the master resume with the Google Drive connector (`read_file_content` on `profile.yaml` → `resume.google_drive_file_id`). Rewrite the
headline, summary, competency order and bullet order/wording to mirror the posting's
language and priorities. **Never invent** employers, titles, dates, metrics or skills.
Produce a Claude Doc of the tailored resume plus a "what changed and why" list.

## 5. Deliver

Publish or update the digest page with the 3 job cards, then end with a one-line
summary per job. The scheduled Routine sends that summary as a push notification.
