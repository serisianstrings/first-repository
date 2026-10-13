"""Parse posted pay strings into annual USD base ranges."""

import re
from typing import Optional, Tuple

_NUM = r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?"
_RANGE = re.compile(_NUM + r"(?:\s*(?:-|–|—|to)\s*" + _NUM + r")?")
_FOREIGN = re.compile(r"(C\$|CA\$|A\$|AU\$|NZ\$|€|£|CAD|EUR|GBP)")
_HOURLY = re.compile(r"\b(an hour|per hour|/hr|/hour|hourly)\b", re.I)
_MONTHLY = re.compile(r"\b(a month|per month|/mo|monthly)\b", re.I)
_OTE = re.compile(r"\b(OTE|on[- ]target|total comp(?:ensation)?)\b", re.I)


def _amount(num: str, suffix: Optional[str]) -> float:
    value = float(num.replace(",", ""))
    if suffix and suffix.lower() == "k":
        value *= 1_000
    elif suffix and suffix.lower() == "m":
        value *= 1_000_000
    return value


def parse_salary(text: Optional[str]) -> Tuple[Optional[int], Optional[int], list]:
    """Return (min, max, notes) as annual USD, or (None, None, notes) when unusable.

    Non-USD amounts are ignored. OTE / total-comp figures are flagged in notes so the
    base-salary rule can treat them as unverified rather than as base pay.
    """
    notes = []
    if not text:
        return None, None, notes
    if _FOREIGN.search(text):
        return None, None, ["non-USD salary"]
    m = _RANGE.search(text)
    if not m:
        return None, None, notes
    low = _amount(m.group(1), m.group(2))
    high = _amount(m.group(3), m.group(4) or m.group(2)) if m.group(3) else low
    # "$228-$342k": the suffix only appears once, on the upper bound.
    if m.group(3) and not m.group(2) and m.group(4) and low < 1_000:
        low = _amount(m.group(1), m.group(4))

    if _HOURLY.search(text):
        low, high = low * 2080, high * 2080
        notes.append("converted from hourly")
    elif _MONTHLY.search(text):
        low, high = low * 12, high * 12
        notes.append("converted from monthly")
    if _OTE.search(text):
        notes.append("OTE/total comp, not base")
    if high < low:
        low, high = high, low
    return int(round(low)), int(round(high)), notes


def meets_base(salary_min, salary_max, notes, min_base=250_000, min_midpoint=225_000) -> str:
    """Classify a posted range against the base-salary bar: pass | fail | unverified."""
    if salary_max is None:
        return "unverified"
    if any("OTE" in n for n in notes):
        return "unverified" if salary_max >= min_base else "fail"
    midpoint = (salary_min + salary_max) / 2
    return "pass" if salary_max >= min_base and midpoint >= min_midpoint else "fail"
