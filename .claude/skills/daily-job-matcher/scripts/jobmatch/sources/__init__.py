"""Alert-email parsers. Each takes a Gmail message dict (id, sender, date, subject,
plaintextBody) as returned by the Gmail connector's get_message(PLAIN_TEXT) and
returns a list of Job records."""

from . import indeed_email, linkedin_email, workingnomads_email

PARSERS = [
    (linkedin_email.SENDERS, linkedin_email.parse),
    (indeed_email.SENDERS, indeed_email.parse),
    (workingnomads_email.SENDERS, workingnomads_email.parse),
]


def parse_message(msg: dict) -> list:
    sender = (msg.get("sender") or "").lower()
    for senders, parse in PARSERS:
        if any(s in sender for s in senders):
            return parse(msg)
    return []
