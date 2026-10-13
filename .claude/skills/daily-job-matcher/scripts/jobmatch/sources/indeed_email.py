"""Indeed job-match emails (donotreply@match.indeed.com), one job per email.

Plain-text body layout after the greeting paragraph:

    Title
    Company
    Location
    Salary: $221,000 - $331,000 a year
    Job type: Full-time
    ...
    View job: https://cts.indeed.com/...
"""

import re

from ..location import classify
from ..models import Job
from ..salary import parse_salary

SENDERS = ("match.indeed.com", "alert@indeed.com", "alert@jobalert.indeed.com")
_VIEW = re.compile(r"View job:\s*(\S+)")
_SALARY = re.compile(r"^Salary:\s*(.+)$", re.M)


def parse(msg: dict) -> list:
    body = msg.get("plaintextBody") or ""
    view = _VIEW.search(body)
    if not view:
        return []
    head = body[:view.start()]
    stop = re.search(r"^(Salary:|Job type:|Benefits:)", head, re.M)
    lines = [ln.strip() for ln in head[:stop.start() if stop else len(head)].splitlines()
             if ln.strip()]
    if len(lines) < 3:
        return []
    title, company, location = lines[-3], lines[-2], lines[-1]
    # The subject ("Title @ Company") is more reliable when the body is unusual.
    subj = msg.get("subject") or ""
    if " @ " in subj:
        title, company = [s.strip() for s in subj.split(" @ ", 1)]

    salary = _SALARY.search(head)
    salary_text = salary.group(1).strip() if salary else None
    lo, hi, notes = parse_salary(salary_text)
    us, remote, city = classify(location)
    return [Job(
        source="indeed", title=title, company=company, location=location,
        url=view.group(1), posted_at=msg.get("date", ""), source_id=msg.get("id"),
        salary_min=lo, salary_max=hi, salary_text=salary_text,
        salary_source="posted" if hi else "none", remote=remote, us_eligible=us,
        preferred_city=city, notes=notes,
    )]
