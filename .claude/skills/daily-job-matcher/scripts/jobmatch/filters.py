"""Hard filters and dedupe applied before Claude scores fit."""

import re
from datetime import datetime, timezone

from .salary import meets_base

_SENIOR = re.compile(
    r"\b(vp|v\.p\.|vice president|svp|evp|head of|chief marketing|cmo|"
    r"(?<!associate )(?<!assistant )(?:senior |sr\.? )?director)\b", re.I)
_FUNCTION = re.compile(
    r"\b(marketing|growth|demand|acquisition|performance|digital|brand|paid|media|"
    r"lifecycle|creative)\b", re.I)
_EXCLUDE = re.compile(
    r"\b(professor|engineer|engineering|designer|sales director|account director|"
    r"art director|creative director|medical director|product manager)\b", re.I)


def title_ok(title: str) -> bool:
    return bool(_SENIOR.search(title) and _FUNCTION.search(title) and not _EXCLUDE.search(title))


def age_hours(posted_at: str, now: datetime) -> float:
    try:
        dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return float("inf")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 3600


def apply(jobs, profile, now=None, seen=frozenset()):
    """Return (kept, rejected) where rejected items carry a reason."""
    now = now or datetime.now(timezone.utc)
    max_age = profile.get("max_posted_age_hours", 72)
    min_base = profile.get("min_base_salary", 250_000)
    min_mid = profile.get("min_range_midpoint", 225_000)
    deal_breakers = [d.lower() for d in profile.get("deal_breakers") or []]

    kept, rejected, by_key = [], [], {}
    for job in jobs:
        reason = None
        if job.key() in seen or (job.source_id and f"{job.source}:{job.source_id}" in seen):
            reason = "already shown"
        elif not title_ok(job.title):
            reason = "title/seniority"
        elif not job.us_eligible:
            reason = "not US-eligible"
        elif age_hours(job.posted_at, now) > max_age:
            reason = "too old"
        elif any(d in f"{job.title} {job.company} {job.location}".lower() for d in deal_breakers):
            reason = "deal-breaker"
        else:
            verdict = meets_base(job.salary_min, job.salary_max, job.notes, min_base, min_mid)
            if verdict == "fail":
                reason = f"salary below bar ({job.salary_text})"
            elif verdict == "unverified":
                job.notes.append("base unverified")
        if reason:
            rejected.append((job, reason))
            continue
        # Dedupe across sources, keeping the record with the most salary information.
        prior = by_key.get(job.key())
        if prior is None:
            by_key[job.key()] = job
            kept.append(job)
        elif job.salary_max and not prior.salary_max:
            kept[kept.index(prior)] = job
            by_key[job.key()] = job
            rejected.append((prior, "duplicate"))
        else:
            rejected.append((job, "duplicate"))
    return kept, rejected
