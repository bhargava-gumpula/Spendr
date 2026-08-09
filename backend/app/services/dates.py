import re
from datetime import date, datetime

_MONTH_DAY_YEAR = re.compile(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})")
_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def parse_deadline(text: str | None) -> date | None:
    """Best-effort date parse from whatever format a source gives us.
    Returns None (never guesses) if the text doesn't contain a recognizable date."""
    if not text:
        return None

    m = _MONTH_DAY_YEAR.search(text)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%b %d %Y").date()
        except ValueError:
            pass

    m = _ISO.search(text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    return None


def days_until(d: date | None, today: date | None = None) -> int | None:
    if d is None:
        return None
    today = today or date.today()
    return (d - today).days
