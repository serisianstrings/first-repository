# Plan: Daily Job Matcher Skill (LinkedIn + Indeed + Working Nomads → Top 3 → Tailored Resume)

## Goal

Every morning, send a **push notification** with **3 jobs** that:

1. Are a **strong match** for my background (VP / Director of Marketing; performance and growth marketing, SaaS and mobile),
2. Were **posted recently** (last 24–72 hours),
3. Pay **$250k+ base salary**,
4. Are **anywhere in the US or remote-US**, ranked with a preference for **Los Angeles, Las Vegas, and Denver**.

Each job card has a **"Tailor my resume"** button that generates a version of my
resume optimized for that role.

## Decisions (answered)

| Question | Answer |
|---|---|
| Target titles | VP of Marketing, Director of Marketing (and close variants; see `profile.yaml`) |
| $250k means | **Base salary** |
| Remote roles | Yes, remote-US counts and is welcome |
| Paid jobs API | Approved |
| Delivery | Push notification each morning, linking to the digest page |
| Job sources | My existing **LinkedIn, Indeed and Working Nomads** saved searches (alert emails in Gmail), plus a paid API |

---

## 1. Job sources

LinkedIn's and Indeed's terms prohibit automated scraping, and LinkedIn bans
accounts that do it. So the skill doesn't log a bot into either site. Each source
is an adapter that outputs the same `Job` record:

| # | Source | How | Notes |
|---|---|---|---|
| A1 | **LinkedIn job alert emails** | Read alerts from Gmail (`from:jobalerts-noreply@linkedin.com newer_than:2d`), parse job ID, title, company, location and link. | My existing saved searches. Primary source. |
| A2 | **Indeed job alert emails** | Read alerts from Gmail (`from:alert@indeed.com newer_than:2d`), parse title, company, location, salary snippet and link. | Indeed alert emails often include the salary line. |
| A3 | **Working Nomads alert emails** | Read alerts from Gmail (`from:workingnomads newer_than:2d`), parse the listings. | Remote-only board; fits the remote-OK preference. |
| B | **Paid jobs API** | JSearch (RapidAPI) as the default, which aggregates LinkedIn, Indeed, Glassdoor and others. Queries per title × location, `date_posted=today/3days`. SerpApi Google Jobs is the backup. | Catches roles my alerts miss and fills thin days. |
| C | **Public job-detail pages / feeds** | For candidates missing a description or salary: fetch the public (logged-out) job page, about 30/day, rate-limited. Working Nomads also has a public JSON feed (`/api/exposed_jobs/`) to try as a supplement. | Needs those domains allowed on the environment's network; not yet verified from this sandbox. |

**Email queries** live in `profile.yaml`, so new alert senders (e.g. a new
saved search) can be added without code changes. The first run lists the
distinct alert subjects it found, so I can confirm all my saved searches are picked up.

---

## 2. Salary handling ($250k base)

- **Pass:** posted base range max ≥ $250k *and* midpoint ≥ $225k (avoids "$120k–$260k" bait ranges).
- **Conditional pass, labeled "Base unverified":** no salary posted, but title and company size strongly suggest $250k+ base (e.g. VP Marketing at a 500+ employee or late-stage company). Show the estimate clearly; at most one such job per digest.
- **Fail:** posted base max < $250k, *or* the range is plainly OTE/total comp below $250k base.
- Normalize hourly/monthly figures; exclude bonus/equity from the base check.
- CA (LA) and CO (Denver) require pay ranges in postings, so those are easy to verify. Nevada (Las Vegas) doesn't, so expect more "unverified" there.

---

## 3. Matching & ranking

**Inputs:** my master resume (stored privately, see §6) and
`.claude/skills/daily-job-matcher/profile.yaml`.

**Strengths the matcher looks for (from my resume):** performance creative &
testing, paid social and programmatic at scale ($10M+/mo), marketing P&L ($25M+),
SaaS acquisition/retention/ARPU, demand gen, CAC and LTV:CAC optimization, MarTech
and ad trafficking automation, team leadership. Industries: fintech/mortgage,
SaaS, telecom, consumer subscription, mobile apps.

**Pipeline**
1. **Collect** from A1–A3 + B (target 50–150 candidates/day).
2. **Dedupe** across sources (normalize company + title + city; LinkedIn/Indeed IDs) and drop anything already in `seen_jobs.json`.
3. **Hard filters:** posted ≤ 72h, salary rule, US/remote-US, title is VP/Head/Senior Director/Director of Marketing (or Growth/Performance/Demand Gen), no deal-breakers.
4. **Claude fit score (0–100):** resume vs. full job description → rationale, top 3 matching strengths, gaps.
5. **Final score** = `0.70 × fit + 0.15 × comp_confidence + 0.15 × location_bonus`
   - location bonus: LA / Las Vegas / Denver = 100, Remote-US = 90, other US = 40.
6. **Pick top 3**, including at least one LA/LV/Denver role when one has fit ≥ 75.
7. If fewer than 3 qualify, show what qualified and why the rest fell short; never pad with weak matches.

---

## 4. Daily delivery

- **Digest page:** a private Artifact page with 3 job cards showing title, company, location (★ for preferred cities, 🌐 for remote), source (LinkedIn/Indeed/Working Nomads/API), posted age, base salary (verified/estimated badge), fit score, why I match, gaps, and an **Apply** link.
- **Push notification:** a Claude Code Routine runs on a fresh session each weekday morning (about 6:45am PT) with push notifications on. The final message is a short summary (e.g. "3 matches today: VP Growth @ X (LA, $260–300k)…") with a link to the digest.
- **Feedback buttons:** "Applied" and "Not interested" write to the page's shared database; future rankings use them, and those jobs won't be shown again.

---

## 5. "Tailor my resume" button

When I click it, the page sends Claude the job (via the artifact's ask-Claude
capability, or a queued request row the next run picks up). Claude then:

1. Loads the master resume and the full job description.
2. Extracts the posting's requirements and keywords (ATS terms).
3. Rewrites the headline and executive summary for the role, reorders core competencies, and leads with the most relevant bullets (e.g. P&L and team scale for VP roles; creative testing and paid social for performance roles). **It never invents** experience, titles, dates or metrics; it only rephrases and highlights what's true.
4. Produces a tailored resume **Claude Doc** (exports to Word/PDF/Google Docs), a "what changed and why" list, and an optional cover-letter draft.
5. Adds the doc link to the job card.

---

## 6. Skill structure

```
.claude/skills/daily-job-matcher/
  SKILL.md                 # trigger + step-by-step instructions
  profile.yaml             # preferences, titles, alert queries (committed; no personal info)
  scripts/
    sources/
      gmail_alerts.py      # A1–A3: LinkedIn / Indeed / Working Nomads alert parsers
      jobs_api.py          # B: JSearch (SerpApi fallback)
      public_page.py       # C: public detail pages / feeds
    normalize.py           # Job schema, salary parsing (base vs OTE)
    filter_rank.py         # hard filters + scoring
    state.py               # seen jobs + feedback
  templates/
    digest.html            # artifact page
    tailor_prompt.md       # tailoring guardrails
  tests/fixtures/          # sample alert emails, salary strings
```

**Resume privacy:** this repo is **public**, so the resume (phone, email) is
**not committed**. It lives in my Google Drive (or another private store) and
the skill reads it at run time. `resume/` is gitignored for local copies.

**Secrets:** the JSearch/SerpApi key goes in the environment's secrets, never in the repo.

---

## 7. Build phases

| Phase | Scope | Done when |
|---|---|---|
| **0. Setup** (me) | Connect **Gmail** at claude.ai/customize/connectors; put the resume in Drive; get a JSearch key and add it to environment secrets; allow job-site domains on the environment's network. | Connectors and key visible to a new session |
| **1. Ingest** | Gmail parsers for all three alert types, JSearch adapter, normalize/dedupe, salary parser + tests. | 1 day of real alerts → clean Job list |
| **2. Match** | Filters, Claude fit scoring, ranking. | Manual run gives 3 sensible picks |
| **3. Digest + push** | Artifact page, Routine with push notification. | Phone gets a notification linking to 3 jobs |
| **4. Tailor** | Button → tailored resume Doc + change list. | One click → resume link on the card |
| **5. Automate & tune** | Seen-jobs state, feedback buttons, weight tuning. | Runs unattended for 5 straight weekdays |

---

## 8. Risks & mitigations

- **Site ToS / account bans** → only alert emails, a licensed API and low-volume public pages; no logged-in scraping.
- **Base vs OTE confusion** → the parser separates base from OTE/total comp; anything ambiguous is labeled "unverified".
- **Missing salary (Las Vegas, remote)** → estimate plus label; max one unverified job per day.
- **Stale or reposted listings** → use the posted date from the source, not the email date; dedupe across sources.
- **Resume hallucination** → strict guardrails plus a change list I review before sending.
- **Thin days** → widen to 72h, then lean on the API; show fewer than 3 rather than weak matches.
