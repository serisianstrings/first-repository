"""Common job record shared by every source adapter."""

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Job:
    source: str                      # linkedin | indeed | workingnomads | jsearch
    title: str
    company: str
    location: str
    url: str
    posted_at: str                   # ISO 8601; email date when the source gives nothing better
    source_id: Optional[str] = None  # LinkedIn job ID, Working Nomads job ID, ...
    salary_min: Optional[int] = None  # annual USD
    salary_max: Optional[int] = None
    salary_text: Optional[str] = None
    salary_source: str = "none"      # posted | estimated | none
    remote: bool = False
    us_eligible: bool = True
    preferred_city: Optional[str] = None
    description: Optional[str] = None
    notes: list = field(default_factory=list)

    def key(self) -> str:
        """Cross-source dedupe key: normalized company + title."""
        norm = lambda s: " ".join("".join(c.lower() if c.isalnum() else " " for c in s).split())
        return f"{norm(self.company)}|{norm(self.title)}"

    def to_dict(self) -> dict:
        return asdict(self)
