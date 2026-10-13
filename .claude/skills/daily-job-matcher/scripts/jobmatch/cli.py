"""Turn saved alert emails into a filtered candidate list.

Usage:
    python3 -m jobmatch.cli candidates messages.json [--profile profile.yaml]
        [--seen seen_jobs.json] [--out candidates.json]

messages.json is a JSON array of Gmail messages as returned by the Gmail connector's
get_message with messageFormat=PLAIN_TEXT (fields: id, sender, date, subject,
plaintextBody). Prints a summary of what was kept and rejected and why.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from . import filters
from .sources import parse_message

SKILL_DIR = Path(__file__).resolve().parents[2]


def load_profile(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML is required: pip install pyyaml")
    return yaml.safe_load(path.read_text()) or {}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="jobmatch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("messages", type=Path)
    c.add_argument("--profile", type=Path, default=SKILL_DIR / "profile.yaml")
    c.add_argument("--seen", type=Path)
    c.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    profile = load_profile(args.profile)
    messages = json.loads(args.messages.read_text())
    seen = frozenset(json.loads(args.seen.read_text())) if args.seen and args.seen.exists() else frozenset()

    jobs = [job for msg in messages for job in parse_message(msg)]
    kept, rejected = filters.apply(jobs, profile, seen=seen)

    reasons = Counter(r if not r.startswith("salary") else "salary below bar" for _, r in rejected)
    print(f"parsed {len(jobs)} jobs from {len(messages)} emails "
          f"({dict(Counter(j.source for j in jobs))})", file=sys.stderr)
    print(f"kept {len(kept)}; rejected: {dict(reasons)}", file=sys.stderr)

    payload = json.dumps([j.to_dict() for j in kept], indent=2)
    if args.out:
        args.out.write_text(payload)
    else:
        print(payload)


if __name__ == "__main__":
    main()
