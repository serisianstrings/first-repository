"""Classify job locations: US eligibility, remote, preferred city."""

import re
from typing import Optional, Tuple

PREFERRED = {
    "Los Angeles": ["los angeles", "santa monica", "culver city", "playa vista", "el segundo",
                    "burbank", "pasadena", "glendale, ca", "long beach", "irvine", "venice, ca"],
    "Las Vegas": ["las vegas", "henderson, nv", "summerlin"],
    "Denver": ["denver", "boulder", "englewood, co", "aurora, co", "lakewood, co", "broomfield",
               "greenwood village", "centennial, co", "golden, co"],
}

_US_STATE = re.compile(
    r",\s*(A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|"
    r"S[CD]|T[NX]|UT|V[AT]|W[AIVY])\b")
_US_WORDS = re.compile(r"\b(united states|usa|u\.s\.|us only|north america|americas)\b", re.I)


def classify(location: str) -> Tuple[bool, bool, Optional[str]]:
    """Return (us_eligible, remote, preferred_city)."""
    loc = (location or "").strip()
    low = loc.lower()
    remote = "remote" in low or "anywhere" in low
    preferred = next((city for city, needles in PREFERRED.items()
                      if any(n in low for n in needles)), None)
    if preferred or _US_STATE.search(loc) or _US_WORDS.search(loc):
        return True, remote, preferred
    # A bare "Remote" from a US alert is treated as US-eligible.
    if low in ("remote", "remote, us", "remote (us)", "hybrid remote"):
        return True, True, None
    return False, remote, None
