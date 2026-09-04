# Requirements refinement

## In scope:

1. Add an alarm (time + optional label, optional repeat-daily flag)
2. List alarms
3. Remove an alarm
4. Run a foreground monitor that rings (terminal bell, macOS system sound when available, and visual banner) at the right time
5. Snooze / dismiss when it rings
6. Persist alarms to a local JSON file so they survive restarts

## Explicitly out of scope

1. No GUI/web/database — per spec
2. No timezone handling — assume local system time, note it as a stated assumption
3. No custom audio files — use the terminal bell (\a), with the built-in macOS system sound as an additional alert when available.
4. No multi-day recurrence rules
