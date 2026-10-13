# Plan: Daily Job Matcher Skill (LinkedIn → Top 3 → Tailored Resume)

## Goal

Every morning, deliver **3 jobs** that:

1. Are a **strong match** for my background,
2. Were **posted recently** (last 24–72 hours),
3. **Pay $250k+** (base, or total comp if base isn't listed — flagged),
4. Are **anywhere in the US**, ranked with a preference for **Los Angeles, Las Vegas, and Denver**.

Each job card has a **"Tailor my resume"** button that generates a version of my
resume optimized for that role.

---

## 1. Key constraint: how we get LinkedIn data

LinkedIn's User Agreement prohibits automated scraping, and it actively bans
accounts that do it. Logging a bot in with my own account puts that account at
risk. So the plan uses **sourcing adapters** behind one interface, picked in
this order:

| Option | How it works | Risk | Reliability |
|---|---|---|---|
| **A. LinkedIn Job Alert emails (recommended)** | Save searches on LinkedIn with email alerts on, then have the skill read the alert emails (Gmail connector) and pull each job's link, title, company and location. | None (LinkedIn sends them to you) | High |
| **B. Third-party jobs API** | Licensed aggregators that include LinkedIn listings (e.g. JSearch on RapidAPI, SerpApi Google Jobs, Apify LinkedIn Jobs actor). Supports query, location, date-posted and sometimes salary filters. | Low; the vendor handles compliance | High; costs about $0–50/mo |
| **C. Public job-detail pages** | Fetch the *public* (logged-out) page for each job ID found via A/B, to get the full description and salary range. Low volume (about 30 fetches/day), rate-limited. | Low–medium | Medium |
| **D. Browser on my own logged-in session** | Claude in Chrome reads search results while I'm signed in. Manual/on-demand only, never scheduled. | Medium | Medium |

**MVP = A + C**, with **B** added if alert volume is too thin. D stays a manual
fallback.

### Search parameters to encode
- Keywords: derived from my resume (target titles plus 2–3 adjacent titles).
- Date posted: past 24h (`f_TPR=r86400`), widened to 72h if fewer than 3 qualify.
- Location: "United States", plus dedicated saved searches for LA, Las Vegas and Denver so preferred cities are never crowded out.
- Salary: LinkedIn's highest salary filter (`f_SB2`, $200k+ bucket), then a hard **$250k** check during parsing (see below).
- Experience level: Director / Executive (and Mid-Senior if titles fit).

---

## 2. Salary handling ($250k bar)

Many postings don't list pay, but pay-transparency laws require ranges in
**CA (LA), CO (Denver)**, NY, WA, IL and others. Nevada doesn't require them,
so Las Vegas roles will often have no salary.

Rules:
- **Pass:** posted range max ≥ $250k *and* midpoint ≥ ~$225k (avoids "$120k–$260k" bait ranges).
- **Conditional pass, labeled "Comp unverified":** no salary listed, but title/level/company strongly suggest $250k+ (e.g. VP or Director at a large company). Estimate using Levels.fyi-style heuristics, and show the estimate clearly.
- **Fail:** posted max < $250k.
- Normalize hourly/monthly figures and "OTE" or "total comp" wording.

---

## 3. Matching & ranking

**Inputs:** my master resume (from Google Drive or a file in this repo) and a short
`profile.yaml` that I edit:

```yaml
target_titles: [...]
must_have: [...]          # skills/domains that must appear
deal_breakers: [...]      # e.g. "on-site 5 days", certain industries
min_base: 250000
preferred_locations: [Los Angeles, Las Vegas, Denver]
open_to: [Remote-US, Relocation-US]
seniority: [Director, Senior Director, VP]
```

**Pipeline**
1. **Collect** candidates from the adapters (target 30–100/day).
2. **Dedupe** by LinkedIn job ID plus company+title (reposts happen often); drop anything already shown in a past digest (`seen_jobs.json`).
3. **Hard filters:** recency, salary rule, US location, deal-breakers, seniority.
4. **LLM fit score (0–100)** with Claude: resume vs. full job description, with a short rationale, top 3 matching strengths, and gaps.
5. **Final score** = `0.70 × fit + 0.15 × comp_confidence + 0.15 × location_bonus`
   - location bonus: LA / Las Vegas / Denver = 100, Remote-US = 70, other US = 40.
6. **Pick top 3**, with at least one preferred-city role if any scores ≥ 75 fit.
7. If fewer than 3 qualify, show what qualified and say why the rest fell short; never pad with weak matches.

---

## 4. Daily delivery: the digest page

A published **Artifact page** (private) refreshed each morning:

- 3 job cards: title, company, location (with a ★ for preferred cities), posted age, salary (with a verified/estimated badge), fit score, a "why you match" note, gaps, and an **Apply on LinkedIn** link.
- **"Tailor my resume" button** on each card (see §5).
- Optional: "Not interested" / "Applied" buttons that write to the page's shared database, so feedback improves later rankings and prevents repeats.
- A short notification (push/email) when the digest is ready.

**Scheduling:** a Claude Code **Routine** (scheduled trigger) that runs on weekdays (or daily)
at about 6:45am Pacific and starts a fresh session each time, running the skill end to end.

---

## 5. "Tailor my resume" button

When I click it, the page sends the job ID and description to Claude (via
the artifact's ask-Claude capability, or by queueing a request row that the next
session picks up). Claude then:

1. Loads the master resume and the job description.
2. Extracts the posting's key requirements and keywords (ATS terms).
3. Rewrites the summary, reorders and rephrases bullets to match the posting's language, and puts relevant experience first. **It never invents experience, titles, dates or metrics**; it only rephrases or highlights what's true.
4. Produces:
   - a tailored resume as a **Claude Doc** (exports to Word/PDF/Google Docs),
   - a short change log ("what changed and why"),
   - an optional cover-letter draft.
5. Adds the doc link back onto the job card.

---

## 6. Skill structure (repo layout)

```
.claude/skills/daily-job-matcher/
  SKILL.md                 # trigger description + step-by-step instructions
  profile.yaml             # my preferences (§3)
  resume/master.md         # source-of-truth resume (or a Drive file ID)
  scripts/
    sources/
      alert_emails.py      # Adapter A: parse LinkedIn alert emails
      jobs_api.py          # Adapter B: JSearch / SerpApi
      public_page.py       # Adapter C: fetch public job detail pages
    normalize.py           # common Job schema, salary parsing
    filter_rank.py         # hard filters + scoring
    state.py               # seen_jobs.json, feedback
  templates/
    digest.html            # artifact page template
    tailor_prompt.md       # resume tailoring instructions + guardrails
  tests/                   # fixtures: sample alert emails, job pages, salary strings
```

`Job` schema: `id, url, title, company, location, remote_type, posted_at,
salary_min, salary_max, salary_source(posted|estimated), description, source`.

---

## 7. Build phases

| Phase | Scope | Done when |
|---|---|---|
| **0. Setup** (about 30 min, me) | Create 4–6 LinkedIn saved searches with daily email alerts; upload resume; fill out `profile.yaml`; connect Gmail; optionally get an API key for Adapter B. | Alerts are arriving and the resume is accessible |
| **1. Ingest** | Adapters A + C, normalize, dedupe, salary parser with unit tests. | 1 day of alerts → clean Job list |
| **2. Match** | Hard filters, Claude fit scoring, ranking, top-3 selection. | Manual run gives 3 sensible picks |
| **3. Digest** | Artifact page plus a notification. | Page shows today's 3 jobs |
| **4. Tailor** | Button → tailored resume Doc + change log. | One click → resume link on the card |
| **5. Automate** | Daily Routine, seen-jobs state, feedback buttons. | Runs unattended for 5 straight days |
| **6. Tune** | Adjust weights based on my feedback; add Adapter B if volume is low. | Ongoing |

---

## 8. Risks & mitigations

- **LinkedIn ToS / account bans** → no logged-in scraping on a schedule; use alerts, licensed APIs and low-volume public pages.
- **Missing salary data (especially Las Vegas)** → "Comp unverified" label plus an estimate; never shown as verified.
- **Stale or reposted listings** → use the posted date from the detail page, not the email date; dedupe reposts.
- **Resume hallucination** → strict prompt guardrails plus a diff/change log I review before sending.
- **Thin days** → widen to 72h first, then Remote-US; show fewer than 3 rather than weak matches.

---

## 9. Open questions for me

1. Target titles/function and seniority (e.g. VP Engineering, Director of Product)?
2. Is $250k **base** or **total comp**?
3. Where does the master resume live (Drive file, PDF, or should I paste it)?
4. Do I count remote-US roles as matches, or only on-site/hybrid in a city I'd move to?
5. Okay to pay for a jobs API (Adapter B) if alert emails alone are too thin?
6. Delivery time and days (weekdays only?), and push vs. email notification?
