import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from jobmatch import filters  # noqa: E402
from jobmatch.location import classify  # noqa: E402
from jobmatch.salary import meets_base, parse_salary  # noqa: E402
from jobmatch.sources import parse_message  # noqa: E402

MESSAGES = json.loads((HERE / "fixtures" / "messages.json").read_text())
NOW = datetime(2026, 10, 13, 14, 0, tzinfo=timezone.utc)
PROFILE = {"min_base_salary": 250_000, "min_range_midpoint": 225_000, "max_posted_age_hours": 72}


def jobs_from(msg_id):
    return parse_message(next(m for m in MESSAGES if m["id"] == msg_id))


class SalaryTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(parse_salary("$221,000 - $331,000 a year")[:2], (221_000, 331_000))
        self.assertEqual(parse_salary("$228k-$342k per year")[:2], (228_000, 342_000))
        self.assertEqual(parse_salary("$160,000 a year")[:2], (160_000, 160_000))
        self.assertEqual(parse_salary("$137,049.64 - $165,049.03 a year")[:2], (137_050, 165_049))
        self.assertEqual(parse_salary("$120 - $140 an hour")[:2], (249_600, 291_200))
        self.assertEqual(parse_salary("€93k-€140k per year")[:2], (None, None))
        self.assertEqual(parse_salary("C$188k-C$282k per year")[:2], (None, None))
        self.assertEqual(parse_salary(None)[:2], (None, None))

    def test_base_rule(self):
        self.assertEqual(meets_base(221_000, 331_000, []), "pass")
        self.assertEqual(meets_base(250_000, 300_000, []), "pass")
        self.assertEqual(meets_base(142_000, 247_000, []), "fail")
        self.assertEqual(meets_base(120_000, 260_000, []), "fail")      # bait range
        self.assertEqual(meets_base(None, None, []), "unverified")
        self.assertEqual(meets_base(200_000, 300_000, ["OTE/total comp, not base"]), "unverified")


class LocationTests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("Santa Monica, CA"), (True, False, "Los Angeles"))
        self.assertEqual(classify("Las Vegas, NV"), (True, False, "Las Vegas"))
        self.assertEqual(classify("Englewood, CO"), (True, False, "Denver"))
        self.assertEqual(classify("Remote"), (True, True, None))
        self.assertEqual(classify("Aventura, FL"), (True, False, None))
        self.assertFalse(classify("Germany, Ireland, UK")[0])
        self.assertTrue(classify("Canada, USA")[0])


class ParserTests(unittest.TestCase):
    def test_linkedin(self):
        jobs = jobs_from("li-1")
        self.assertEqual([j.title for j in jobs],
                         ["VP, Growth Marketing", "General Manager, Ads", "Director of Performance Marketing"])
        self.assertEqual(jobs[0].company, "Flex")
        self.assertEqual(jobs[0].url, "https://www.linkedin.com/jobs/view/4451560473/")
        self.assertEqual(jobs[2].preferred_city, "Las Vegas")
        self.assertIsNone(jobs[0].salary_max)

    def test_indeed(self):
        (job,) = jobs_from("in-1")
        self.assertEqual((job.title, job.company, job.location), ("Director, Growth Marketing", "Indeed", "Remote"))
        self.assertEqual((job.salary_min, job.salary_max), (221_000, 331_000))
        self.assertTrue(job.remote)

    def test_working_nomads(self):
        jobs = jobs_from("wn-1")
        self.assertEqual(len(jobs), 4)
        head = next(j for j in jobs if j.source_id == "1671500")
        self.assertEqual((head.title, head.company), ("Head of Growth - Marketing", "Example Co"))
        self.assertEqual(head.posted_at, "2026-10-12")
        self.assertEqual(head.salary_max, 300_000)
        emea = next(j for j in jobs if j.source_id == "1671028")
        self.assertFalse(emea.us_eligible)


class FilterTests(unittest.TestCase):
    def test_title(self):
        for t in ["VP, Growth Marketing", "Director of Performance Marketing", "Head of Growth",
                  "Senior Director, Digital Marketing", "Chief Marketing Officer"]:
            self.assertTrue(filters.title_ok(t), t)
        for t in ["General Manager, Ads", "Senior Staff Product Designer", "Assistant Professor, Marketing",
                  "Associate Director, Marketing", "Sr. Manager, User Acquisition"]:
            self.assertFalse(filters.title_ok(t), t)

    def test_pipeline(self):
        jobs = [j for m in MESSAGES for j in parse_message(m)]
        kept, rejected = filters.apply(jobs, PROFILE, now=NOW)
        kept_titles = {(j.company, j.title) for j in kept}
        self.assertIn(("Indeed", "Director, Growth Marketing"), kept_titles)
        self.assertIn(("Example Co", "Head of Growth - Marketing"), kept_titles)
        # No salary posted: kept but flagged.
        flex = next(j for j in kept if j.company == "Flex")
        self.assertIn("base unverified", flex.notes)
        reasons = {(j.company, r) for j, r in rejected}
        self.assertIn(("SafelyYou", "salary below bar ($155,000 - $180,000 a year)"), reasons)
        self.assertIn(("eBay", "title/seniority"), reasons)
        self.assertIn(("EMEA Co", "not US-eligible"), reasons)

    def test_seen_and_dedupe(self):
        jobs = jobs_from("in-1") + jobs_from("in-1")
        kept, rejected = filters.apply(jobs, PROFILE, now=NOW)
        self.assertEqual(len(kept), 1)
        self.assertEqual(rejected[0][1], "duplicate")
        kept, _ = filters.apply(jobs_from("in-1"), PROFILE, now=NOW, seen={"indeed|director growth marketing"})
        self.assertEqual(kept, [])

    def test_too_old(self):
        kept, rejected = filters.apply(jobs_from("in-1"), PROFILE, now=datetime(2026, 10, 20, tzinfo=timezone.utc))
        self.assertEqual(rejected[0][1], "too old")


if __name__ == "__main__":
    unittest.main()
