---
name: rAImind
description: >
  Creates Microsoft Outlook calendar reminders from plain language in any conversation.
  Use this skill whenever the user wants to set a reminder, schedule something, create
  a calendar event, or says things like "remind me", "don't let me forget", "set a reminder",
  "add to my calendar", "every Monday remind me", "show me my reminders", or
  "set up sprint reminders". Generates a standard .ics file and opens it directly in
  Outlook for Mac — one click to confirm and the event lands in Exchange with a popup alarm.
  Supports timed reminders, all-day reminders, recurring weekly reminders, team-aware events
  (colleague name noted in description), sprint setup (4 events in one command), and listing
  all upcoming reminders. Note: currently macOS only (Outlook for Mac).
---

Creates Microsoft Outlook calendar reminders from plain language. Just say what you need to remember — rAImind generates a .ics file and opens it in Outlook for Mac. One click to confirm and it's in your Exchange calendar.

> **Platform:** macOS only (Outlook for Mac). Windows support is planned — see roadmap below.

## Usage

`/raimind` or just say it naturally:
- "Remind me tomorrow at 9am to update the onepager"
- "Every Monday at 9am remind me to update the sprint log"
- "Set up sprint reminders, sprint starts 28 July ends 22 August"
- "Show me my rAIminds"

---

## Prerequisites

- macOS with Microsoft Outlook installed
- Python 3 (`python3 --version`)
- `python-dateutil` installed: `pip3 install python-dateutil`
- Script saved to `~/.claude/tools/remind.py` (see installation below)

---

## Installation

1. Install dependency: `pip3 install python-dateutil`
2. Copy the script from this repo to your Claude tools folder:
   ```bash
   cp skills/raimind/remind.py ~/.claude/tools/remind.py
   ```
   Or download it directly from [github.com/tereziamacingova/sap-ai-skills](https://github.com/tereziamacingova/sap-ai-skills/blob/main/skills/raimind/remind.py)
3. Add the following to your `~/.claude/CLAUDE.md`:

```markdown
### `/raimind` — rAImind: Outlook Calendar Reminder

**Trigger:** `/raimind` or any of:
- "remind me [time] to [task]"
- "set a reminder for [time] to [task]"
- "don't let me forget [time] to [task]"
- "every Monday remind me to [task]"
- "show me my rAIminds" / "list my reminders"
- "set up sprint reminders for sprint starting [date] ending [date]"

Creates calendar events prefixed with `[rAImind]` in Outlook for Mac via .ics import.
Timed reminders are 5-minute Free events with a popup alarm.
No time = all-day event. Colleagues noted in description only — no invites sent.

- **Script:** `~/.claude/tools/remind.py`
- **Log:** `~/.claude/tools/raimind_log.json`

**Usage patterns:**
- Basic: `python3 ~/.claude/tools/remind.py "tomorrow at 9am update the onepager"`
- All-day: `python3 ~/.claude/tools/remind.py "tomorrow update the slides"`
- Recurring: `python3 ~/.claude/tools/remind.py "every Monday at 9am update the sprint log"`
- With colleague: `python3 ~/.claude/tools/remind.py "tomorrow at 10am standup" --with "Lucas"`
- With description: `python3 ~/.claude/tools/remind.py "tomorrow at 9am review PR" --desc "focus on auth flow"`
- Sprint: `python3 ~/.claude/tools/remind.py sprint "2026-07-28" "2026-08-22"`
- List: `python3 ~/.claude/tools/remind.py list`

**After running:** Confirm the scheduled time and title back to the user.
For sprint reminders, confirm all 4 events.
```

---

## Examples

| What you say | What gets created |
|---|---|
| "Remind me tomorrow at 9am to update the onepager" | 5-min event at 09:00, popup alarm |
| "Remind me Friday to review the sprint slides" | All-day event on Friday |
| "Every Monday at 9am remind me to update the sprint log" | Weekly recurring event |
| "Remind me and Lucas on Friday to review the integration" | Event with "With: Lucas" in description |
| "Set up sprint reminders, sprint starts 28 July ends 22 August" | 4 events: start · 3-days-before · SFM review Wed · SCT review Thu |
| "Show me my rAIminds" | Summary of all upcoming reminders |

---

## How it works

1. Claude detects the reminder intent from natural language
2. Calls `remind.py` with the parsed date, time, and title
3. Script generates a `.ics` calendar file
4. Outlook opens the import dialog — user clicks to confirm
5. Event appears in Exchange calendar with popup alarm

---

## Roadmap

- **Windows support** — the .ics file format is cross-platform; only the auto-open step needs updating (`os.startfile()` on Windows vs `open` on macOS). Contribution welcome.
