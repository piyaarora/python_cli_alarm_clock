# Alarm Clock CLI

## Problem framing

The brief was intentionally open ("build an alarm clock as a CLI, decide scope
yourself"). Before writing code, I scoped it down to something achievable and
demoable in the time available, and wrote the scope down explicitly rather
than guessing silently:

**In scope**

- Add an alarm: time, optional label, optional daily repeat
- List alarms
- Remove an alarm
- A foreground `start` command that monitors and rings alarms
- Snooze (5 min) or dismiss when an alarm rings
- Persistence to a local JSON file, so alarms survive restarts

**Explicitly out of scope** (and why)

- **No GUI/web/DB** .
- **No timezones** — uses system local time; noted as an assumption rather than silently guessed.
- **No custom audio files** — rings via the terminal bell (`\a`) plus a visual banner. On macOS, it also plays the built-in `Glass.aiff` system sound through `afplay`. This avoids an external audio dependency that may not behave consistently across OSes/headless environments, which isn't worth the risk in a short exercise.
- **No complex recurrence** (specific weekdays, multiple repeats) — only "once" or "every day," to keep the data model and monitor loop simple.
- **No system-level scheduling** — `start` is a blocking foreground process you run in a terminal, which is enough to demonstrate the logic without OS-specific service code.

## Design

- **Data model**: a single `Alarm` dataclass (`id`, `time`, `label`, `repeat_daily`, `enabled`, `last_fired_date`). `last_fired_date` prevents
  an alarm from re-firing multiple times within the same minute, and lets a daily alarm know it already fired today.
- **Storage**: flat JSON file (`alarms.json`), written via a temp-file + atomic-replace pattern so a crash mid-write can't corrupt the store. A database was explicitly out of scope, and JSON is more than sufficient for a single-user, single-machine list of alarms.
- **Monitor loop** (`start`): polls once per second, compares `HH:MM` against each enabled alarm. Polling is simple and easy to reason about;
  a production version would likely use a proper scheduler (e.g.
  `sched`/APScheduler) to avoid a busy-ish loop, but that's overkill here.
- **CLI shape**: `argparse` subcommands (`add`, `list`, `remove`, `start`)
  rather than an interactive menu, so each action is scriptable and
  testable independently.

## How I used AI

I used Claude to:

1. Talk through scope for a vague prompt and explicitly separate "in scope" vs. "out of scope" before writing any code.
2. Draft the initial implementation from that scope (dataclass model, JSON persistence, argparse CLI, monitor loop).
3. Generate and run a small test suite covering time validation and the storage round-trip.
   I reviewed the generated code line by line, ran it manually against each command (`add`, `list`, `remove`, an invalid time), and ran the test suite
   before accepting it — see the screen recording for the walkthrough.

## Usage

```bash
# Add an alarm
python3 alarm_clock.py add 07:30 --label "Wake up" --repeat

# Add a one-off alarm
python3 alarm_clock.py add 09:00 --label "Standup"

# List alarms
python3 alarm_clock.py list

# Remove an alarm by id
python3 alarm_clock.py remove 2

# Start monitoring (blocks; rings at the scheduled time; Ctrl+C to stop)
python3 alarm_clock.py start
```

When an alarm fires, it rings the terminal bell, plays the built-in macOS
system alert sound when available, prints a banner, and prompts:

```
[Enter] dismiss, [s] snooze 5 min:
```

## Tests

```bash
python3 test_alarm_clock.py -v
```

Covers time-string validation and the JSON save/load round trip.

## Requirements

Python 3.9+, standard library only — no `pip install` needed.

## Known limitations / what I'd add with more time

- No custom audio file support (uses the terminal bell and macOS system alert sound)
- No weekday-specific recurrence (e.g. "weekdays only")
- `start` is a single blocking loop rather than a background daemon/service
- No concurrent-write protection if two instances run at once
