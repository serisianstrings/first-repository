"""LinkedIn job alert digests (jobalerts-noreply@linkedin.com).

Plain-text body layout, one block per job separated by dashed lines:

    Title
    Company
    Location
    [badges such as "This company is actively hiring"]
    View job: https://www.linkedin.com/comm/jobs/view/<id>/?...

LinkedIn alerts carry no salary; that comes from the detail page or the jobs API.
"""

import re

from ..location import classify
from ..models import Job

SENDERS = ("jobalerts-noreply@linkedin.com",)
_VIEW = re.compile(r"View job:\s*https://www\.linkedin\.com/(?:comm/)?jobs/view/(\d+)")
_BADGES = ("actively hiring", "apply with resume", "school alum", "connection", "easy apply",
           "promoted", "be an early applicant")


def parse(msg: dict) -> list:
    body = msg.get("plaintextBody") or ""
    jobs = []
    for block in re.split(r"\n-{10,}\n", body):
        m = _VIEW.search(block)
        if not m:
            continue
        lines = [ln.strip() for ln in block[:m.start()].splitlines() if ln.strip()]
        lines = [ln for ln in lines
                 if not ln.lower().startswith("your job alert for")
                 and not any(b in ln.lower() for b in _BADGES)]
        if len(lines) < 3:
            continue
        title, company, location = lines[-3], lines[-2], lines[-1]
        us, remote, city = classify(location)
        job_id = m.group(1)
        jobs.append(Job(
            source="linkedin", title=title, company=company, location=location,
            url=f"https://www.linkedin.com/jobs/view/{job_id}/", posted_at=msg.get("date", ""),
            source_id=job_id, remote=remote, us_eligible=us, preferred_city=city,
        ))
    return jobs
