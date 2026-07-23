#!/usr/bin/env python3
"""
remind.py — rAImind: smart Outlook reminders from natural language.

Usage:
    python3 remind.py "tomorrow at 9am update the AEM onepager"
    python3 remind.py "tomorrow update the AEM onepager"              # all-day
    python3 remind.py "every Monday at 9am update the sprint log"     # recurring
    python3 remind.py "tomorrow at 9am standup" --with "Alice, Bob" # note colleagues (no invite sent)
    python3 remind.py "tomorrow at 9am standup" --desc "Agenda: ..."  # add description
    python3 remind.py "monday from 9 to 11 work on presentations" --busy  # blocker, shown as busy
    python3 remind.py list                                             # list upcoming rAIminds
    python3 remind.py sprint "2026-07-28" "2026-08-22"                # sprint reminders

Setup (one-time):
    pip3 install python-dateutil

Requirements:
    - Python 3 (built-in on macOS)
    - Microsoft Outlook for Mac
    - python-dateutil
"""

import re
import sys
import json
import subprocess
import tempfile
import os
from datetime import datetime, timedelta, date
from dateutil import parser as dateutil_parser

PREFIX = "[rAImind]"
LOG_FILE = os.path.expanduser("~/.claude/tools/raimind_log.json")

RECUR_DAYS = {
    "monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH",
    "friday": "FR", "saturday": "SA", "sunday": "SU",
    "day": None, "weekday": None,
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_reminder(title, when_str, is_all_day, recurring=None, colleagues=None):
    entries = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            try:
                entries = json.load(f)
            except Exception:
                entries = []
    entries.append({
        "title": title,
        "when": when_str,
        "all_day": is_all_day,
        "recurring": recurring,
        "colleagues": colleagues or [],
        "created": datetime.now().isoformat(),
    })
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def cmd_list():
    if not os.path.exists(LOG_FILE):
        print("No rAIminds logged yet.")
        return
    with open(LOG_FILE) as f:
        try:
            entries = json.load(f)
        except Exception:
            print("Could not read log.")
            return
    if not entries:
        print("No rAIminds logged yet.")
        return
    now = datetime.now()
    upcoming = []
    for e in entries:
        try:
            when = datetime.fromisoformat(e["when"]) if "T" in e["when"] else datetime.strptime(e["when"], "%Y-%m-%d")
            if when >= now or e.get("recurring"):
                upcoming.append((when, e))
        except Exception:
            upcoming.append((now, e))
    upcoming.sort(key=lambda x: x[0])
    print(f"\n{'='*55}")
    print(f"  {PREFIX} Upcoming reminders")
    print(f"{'='*55}")
    for when, e in upcoming:
        tag = " [recurring]" if e.get("recurring") else ""
        cols = f" (with: {', '.join(e['colleagues'])})" if e.get("colleagues") else ""
        print(f"  {when.strftime('%a %d %b')}  {e['title']}{tag}{cols}")
    print(f"{'='*55}\n")


# ---------------------------------------------------------------------------
# Natural language -> (when, is_all_day, title, rrule, duration_mins)
# ---------------------------------------------------------------------------

def parse_reminder(text: str):
    now = datetime.now().replace(second=0, microsecond=0)
    original = text.strip()

    # --- "from HH to HH" duration pattern (strip and compute duration) ---
    duration_mins = 5
    from_to = re.search(r"\bfrom\s+([\d:]+\s*(?:am|pm)?)\s+to\s+([\d:]+\s*(?:am|pm)?)\b", original, re.IGNORECASE)
    if from_to:
        t_start = _parse_time_str(from_to.group(1).strip())
        t_end   = _parse_time_str(from_to.group(2).strip())
        duration_mins = (t_end[0] * 60 + t_end[1]) - (t_start[0] * 60 + t_start[1])
        if duration_mins <= 0:
            duration_mins = 60
        # replace "from X to Y" with "at X", preserve surrounding text cleanly
        before = original[:from_to.start()].rstrip()
        after  = original[from_to.end():].lstrip()
        original = (before + f" at {from_to.group(1)} " + after).strip()

    # --- recurring: "every Monday [at 9am] ..." ---
    m = re.match(
        r"^every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|day|weekday)"
        r"(?:\s+at\s+([\d:]+\s*(?:am|pm)?))?\s+",
        original, re.IGNORECASE
    )
    if m:
        unit = m.group(1).lower()
        time_str = m.group(2)
        title = original[m.end():].strip() or original
        if unit == "day":
            rrule = "RRULE:FREQ=DAILY"
            base = now.replace(hour=9, minute=0)
        elif unit == "weekday":
            rrule = "RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
            base = _next_weekday("monday", now)
        else:
            day_code = RECUR_DAYS[unit]
            rrule = f"RRULE:FREQ=WEEKLY;BYDAY={day_code}"
            base = _next_weekday(unit, now)
        if time_str:
            base = _apply_time(base, time_str.strip())
            is_all_day = False
        else:
            base = base.date() if hasattr(base, "date") else base
            is_all_day = True
        return base, is_all_day, title, rrule, duration_mins

    # --- one-off patterns ---
    patterns = [
        (r"^in\s+(\d+)\s+(minute|minutes|hour|hours|day|days)\s+", _parse_in, True),
        (r"^tomorrow\s+at\s+([\d:]+\s*(?:am|pm)?)\s+", _parse_tomorrow_at, True),
        (r"^tomorrow\s+", _parse_tomorrow_allday, False),
        (r"^today\s+at\s+([\d:]+\s*(?:am|pm)?)\s+", _parse_today_at, True),
        (r"^next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+([\d:]+\s*(?:am|pm)?)\s+", _parse_next_weekday_at, True),
        (r"^next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+", _parse_next_weekday_allday, False),
        (r"^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+([\d:]+\s*(?:am|pm)?)\s+", _parse_this_weekday_at, True),
        (r"^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+", _parse_this_weekday_allday, False),
        (r"^on\s+(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\s+at\s+([\d:]+\s*(?:am|pm)?)\s+", _parse_on_date_at, True),
        (r"^on\s+(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\s+", _parse_on_date_allday, False),
    ]
    for pattern, handler, has_time in patterns:
        m = re.match(pattern, original, re.IGNORECASE)
        if m:
            when = handler(m, now)
            title = original[m.end():].strip() or original
            return when, not has_time, title, None, duration_mins

    # Fallback: dateutil
    words = original.split()
    for end in range(min(6, len(words)), 0, -1):
        candidate = " ".join(words[:end])
        try:
            when = dateutil_parser.parse(candidate, default=now, dayfirst=True)
            if when <= now:
                when += timedelta(days=1)
            title = " ".join(words[end:]).strip() or original
            is_all_day = (when.hour == now.hour and when.minute == now.minute)
            return when, is_all_day, title, None, duration_mins
        except Exception:
            continue

    return (now + timedelta(days=1)).date(), True, original, None, duration_mins


def _parse_time_str(s):
    s = s.strip().lower()
    am_pm = None
    if s.endswith("am"):   am_pm, s = "am", s[:-2].strip()
    elif s.endswith("pm"): am_pm, s = "pm", s[:-2].strip()
    if ":" in s:
        h, mn = map(int, s.split(":", 1))
    else:
        h, mn = int(s), 0
    if am_pm == "pm" and h != 12: h += 12
    elif am_pm == "am" and h == 12: h = 0
    return h, mn

def _parse_in(m, now):
    amount, unit = int(m.group(1)), m.group(2).lower()
    if "minute" in unit: return now + timedelta(minutes=amount)
    if "hour" in unit:   return now + timedelta(hours=amount)
    return (now + timedelta(days=amount)).replace(hour=9, minute=0)

def _parse_tomorrow_at(m, now):     return _apply_time(now + timedelta(days=1), m.group(1).strip())
def _parse_tomorrow_allday(m, now): return (now + timedelta(days=1)).date()
def _parse_today_at(m, now):        return _apply_time(now, m.group(1).strip())

def _parse_next_weekday_at(m, now):
    return _apply_time(_next_weekday(m.group(1), now), m.group(2).strip())

def _parse_next_weekday_allday(m, now):
    return _next_weekday(m.group(1), now).date()

def _parse_this_weekday_at(m, now):
    return _apply_time(_next_weekday(m.group(1), now), m.group(2).strip())

def _parse_this_weekday_allday(m, now):
    return _next_weekday(m.group(1), now).date()

def _parse_on_date_at(m, now):     return _apply_time(_on_date(m, now), m.group(4).strip())
def _parse_on_date_allday(m, now): return _on_date(m, now).date()

def _next_weekday(name, now):
    days = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
    target = days[name.lower()]
    ahead = (target - now.weekday() + 7) % 7 or 7
    return (now + timedelta(days=ahead)).replace(hour=9, minute=0)

def _on_date(m, now):
    day, month = int(m.group(1)), int(m.group(2))
    year = int(m.group(3)) if m.group(3) else now.year
    if year < 100: year += 2000
    base = now.replace(year=year, month=month, day=day, hour=9, minute=0)
    if base <= now: base = base.replace(year=base.year + 1)
    return base

def _apply_time(base, time_str):
    h, mn = _parse_time_str(time_str)
    return base.replace(hour=h, minute=mn, second=0, microsecond=0)


# ---------------------------------------------------------------------------
# .ics -> Outlook
# ---------------------------------------------------------------------------

def create_event(when, is_all_day: bool, title: str,
                 description: str = "", rrule: str = None, colleagues: list = None,
                 busy: bool = False, duration_mins: int = 5):
    safe_title = title.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    full_title = f"{PREFIX} {safe_title}"

    desc_parts = []
    if description:
        desc_parts.append(description)
    if colleagues:
        desc_parts.append("With: " + ", ".join(colleagues))
    full_desc = " | ".join(desc_parts)

    if is_all_day:
        day = when if isinstance(when, date) and not isinstance(when, datetime) else when.date()
        dtstart = f"DTSTART;VALUE=DATE:{day.strftime('%Y%m%d')}"
        dtend   = f"DTEND;VALUE=DATE:{day.strftime('%Y%m%d')}"
        transp  = "TRANSPARENT"
        alarm_lines = []
    else:
        end = when + timedelta(minutes=duration_mins)
        dtstart = f"DTSTART:{when.strftime('%Y%m%dT%H%M%S')}"
        dtend   = f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}"
        transp  = "OPAQUE" if busy else "TRANSPARENT"
        alarm_lines = [
            "BEGIN:VALARM",
            "TRIGGER:PT0S",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{full_title}",
            "END:VALARM",
        ]

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//rAImind//EN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        dtstart,
        dtend,
        f"SUMMARY:{full_title}",
        f"TRANSP:{transp}",
        *([ f"DESCRIPTION:{full_desc}" ] if full_desc else []),
        *([ rrule ] if rrule else []),
        *alarm_lines,
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]

    ics = "\r\n".join(lines)
    tmp = tempfile.NamedTemporaryFile(suffix=".ics", delete=False, mode="w", encoding="utf-8")
    tmp.write(ics)
    tmp.close()
    subprocess.run(["open", "-a", "Microsoft Outlook", tmp.name], check=True)


# ---------------------------------------------------------------------------
# Sprint reminder set
# ---------------------------------------------------------------------------

def cmd_sprint(sprint_start: str, sprint_end: str):
    try:
        start = datetime.strptime(sprint_start, "%Y-%m-%d")
        end   = datetime.strptime(sprint_end,   "%Y-%m-%d")
    except ValueError:
        print("Error: dates must be YYYY-MM-DD format")
        sys.exit(1)

    review_wed = end - timedelta(days=(end.weekday() - 2) % 7)
    review_thu = end - timedelta(days=(end.weekday() - 3) % 7)
    three_days_before = end - timedelta(days=3)

    reminders = [
        (start.replace(hour=9, minute=0),             "Sprint start — confirm sprint goal and capacity"),
        (three_days_before.replace(hour=9, minute=0), "Sprint end in 3 days — review open items"),
        (review_wed.replace(hour=9, minute=0),        "SFM Sprint Review today"),
        (review_thu.replace(hour=9, minute=0),        "SCT Sprint Review today"),
    ]

    print(f"\n  {PREFIX} Sprint reminders ({sprint_start} → {sprint_end})")
    for when, title in reminders:
        label = when.strftime("%a %d %b at %H:%M")
        print(f"    • {label}  —  {title}")
        create_event(when, False, title)
        log_reminder(title, when.strftime("%Y-%m-%dT%H:%M"), False)

    print(f"\n  Accept all {len(reminders)} dialogs in Outlook ✓\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _split_flag(args_str, flag):
    marker = f" {flag} "
    if marker in args_str:
        parts = args_str.split(marker, 1)
        return parts[0].strip(), parts[1].strip()
    # flag at end with no value — treat as boolean
    if args_str.endswith(f" {flag}"):
        return args_str[: -len(f" {flag}")].strip(), "true"
    return args_str.strip(), ""


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 remind.py "tomorrow at 9am update the AEM onepager"')
        sys.exit(1)

    if sys.argv[1] == "list":
        cmd_list()
        return

    if sys.argv[1] == "sprint":
        if len(sys.argv) < 4:
            print('Usage: python3 remind.py sprint "2026-07-28" "2026-08-22"')
            sys.exit(1)
        cmd_sprint(sys.argv[2], sys.argv[3])
        return

    raw = " ".join(sys.argv[1:])
    raw, description = _split_flag(raw, "--desc")
    raw, with_str    = _split_flag(raw, "--with")
    raw, busy_str    = _split_flag(raw, "--busy")
    busy = bool(busy_str)

    colleagues = []
    if with_str:
        for name in re.split(r"[,;]\s*|\s+and\s+", with_str):
            name = name.strip()
            if name:
                colleagues.append(name.capitalize())

    when, is_all_day, title, rrule, duration_mins = parse_reminder(raw.strip())

    if is_all_day:
        day = when if isinstance(when, date) and not isinstance(when, datetime) else when.date()
        label = day.strftime("%A, %d %b %Y") + " (all day)"
        when_str = day.strftime("%Y-%m-%d")
    else:
        status = "busy" if busy else ("recurring" if rrule else f"{duration_mins} min, free")
        label = when.strftime("%A, %d %b %Y at %H:%M") + f" [{status}]"
        when_str = when.strftime("%Y-%m-%dT%H:%M")

    print(f'  {PREFIX} "{title}"')
    print(f"       When: {label}")
    if colleagues: print(f"       With: {', '.join(colleagues)} (noted in description — no invite sent)")
    if description: print(f"       Note: {description}")

    create_event(when, is_all_day, title, description, rrule, colleagues, busy, duration_mins)
    log_reminder(title, when_str, is_all_day, rrule, colleagues)
    print("    Outlook: click Accept to confirm ✓")


if __name__ == "__main__":
    main()
