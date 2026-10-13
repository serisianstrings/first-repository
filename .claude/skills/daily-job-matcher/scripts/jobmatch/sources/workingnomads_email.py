"""Working Nomads daily digests (hello@workingnomads.com), about 10–40 remote jobs per email.

Each job is one table row in the plain-text body:

    | Title - Company[](https://newsletter.workingnomads.com/jobs/go/<id>/<user>/) * Regions | Full Time | Senior Level | Monday, Oct 12 * $228k-$342k per year |

The salary segment is optional. Titles may contain " - ", so the company is the
text after the last " - " before the link.
"""

import re
from datetime import datetime

from ..location import classify
from ..models import Job
from ..salary import parse_salary

SENDERS = ("workingnomads.com",)
_ROW = re.compile(
    r"\|\s*(?P<name>[^|\[\]]+?)\[\]\((?P<url>https://newsletter\.workingnomads\.com/jobs/go/"
    r"(?P<id>\d+)/[^)]*)\)\s*\*\s*(?P<rest>[^\n]*?)\s*\|\s*$", re.M)
_DAY = re.compile(r"\b(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,\s+([A-Z][a-z]{2})\s+(\d{1,2})\b")


def _posted(rest: str, email_date: str) -> str:
    m = _DAY.search(rest)
    if not m or not email_date:
        return email_date
    try:
        sent = datetime.fromisoformat(email_date.replace("Z", "+00:00"))
        posted = datetime.strptime(f"{m.group(1)} {m.group(2)} {sent.year}", "%b %d %Y")
        if posted.month > sent.month:            # digest sent in January for a December post
            posted = posted.replace(year=sent.year - 1)
        return posted.date().isoformat()
    except ValueError:
        return email_date


def parse(msg: dict) -> list:
    body = msg.get("plaintextBody") or ""
    jobs = []
    for m in _ROW.finditer(body):
        name = m.group("name").strip()
        title, _, company = name.rpartition(" - ")
        if not title:
            title, company = name, ""
        segments = [s.strip() for s in m.group("rest").split("|")]
        regions = segments[0]
        salary_text = None
        last = segments[-1]
        if " * " in last:
            last, salary_text = [s.strip() for s in last.split(" * ", 1)]
        lo, hi, notes = parse_salary(salary_text)
        us, _, city = classify(regions)
        jobs.append(Job(
            source="workingnomads", title=title.strip(), company=company.strip(),
            location=f"Remote ({regions})", url=m.group("url"),
            posted_at=_posted(last, msg.get("date", "")), source_id=m.group("id"),
            salary_min=lo, salary_max=hi, salary_text=salary_text,
            salary_source="posted" if hi else "none", remote=True, us_eligible=us,
            preferred_city=city, notes=notes,
        ))
    return jobs
