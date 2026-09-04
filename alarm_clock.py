from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

STORE_PATH = Path(__file__).parent / "alarms.json"


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

@dataclass
class Alarm:
    id: int
    time: str            # "HH:MM", 24-hour, local time
    label: str = ""
    repeat_daily: bool = False
    enabled: bool = True
    # Tracks the date (YYYY-MM-DD) this alarm last fired, so a one-off
    # alarm doesn't re-fire twice in the same minute, and so we know
    # whether a "repeat_daily" alarm already fired today.
    last_fired_date: Optional[str] = None


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------

def load_alarms() -> list[Alarm]:
    if not STORE_PATH.exists():
        return []
    try:
        raw = json.loads(STORE_PATH.read_text())
    except json.JSONDecodeError:
        print(f"Warning: {STORE_PATH} is corrupted. Starting with no alarms.", file=sys.stderr)
        return []
    return [Alarm(**item) for item in raw]


def save_alarms(alarms: list[Alarm]) -> None:
    # Write to a temp file then replace, so a crash mid-write can't
    # corrupt the store.
    tmp_path = STORE_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps([asdict(a) for a in alarms], indent=2))
    tmp_path.replace(STORE_PATH)


def next_id(alarms: list[Alarm]) -> int:
    return max((a.id for a in alarms), default=0) + 1


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def parse_time_str(value: str) -> str:
    """Validate an HH:MM 24-hour time string; returns it normalized."""
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a valid time. Use 24-hour HH:MM, e.g. 07:30 or 23:15."
        )
    return parsed.strftime("%H:%M")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_add(args: argparse.Namespace) -> None:
    alarms = load_alarms()
    alarm = Alarm(
        id=next_id(alarms),
        time=args.time,
        label=args.label or "",
        repeat_daily=args.repeat,
    )
    alarms.append(alarm)
    save_alarms(alarms)
    repeat_note = " (repeats daily)" if alarm.repeat_daily else ""
    label_note = f" — {alarm.label}" if alarm.label else ""
    print(f"Added alarm #{alarm.id}: {alarm.time}{repeat_note}{label_note}")


def cmd_list(_args: argparse.Namespace) -> None:
    alarms = load_alarms()
    if not alarms:
        print("No alarms set.")
        return
    print(f"{'ID':<4}{'TIME':<8}{'REPEAT':<9}{'ENABLED':<9}LABEL")
    for a in sorted(alarms, key=lambda a: a.time):
        print(
            f"{a.id:<4}{a.time:<8}{'daily' if a.repeat_daily else 'once':<9}"
            f"{'yes' if a.enabled else 'no':<9}{a.label}"
        )


def cmd_remove(args: argparse.Namespace) -> None:
    alarms = load_alarms()
    remaining = [a for a in alarms if a.id != args.id]
    if len(remaining) == len(alarms):
        print(f"No alarm with id {args.id}.", file=sys.stderr)
        sys.exit(1)
    save_alarms(remaining)
    print(f"Removed alarm #{args.id}.")


def play_alert_sound() -> None:
    if sys.platform == "darwin":
        try:
            subprocess.Popen(
                ["/usr/bin/afplay", "/System/Library/Sounds/Glass.aiff"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass


def ring(alarm: Alarm) -> None:
    """Ring the alarm: bell + banner, then prompt for snooze/dismiss."""
    banner = f" ALARM: {alarm.time} {('— ' + alarm.label) if alarm.label else ''} "
    border = "=" * len(banner)
    play_alert_sound()
    for _ in range(3):
        sys.stdout.write("\a")  # terminal bell
        sys.stdout.flush()
        time.sleep(0.3)
    print(f"\n{border}\n{banner}\n{border}")

    while True:
        choice = input("[Enter] dismiss, [s] snooze 5 min: ").strip().lower()
        if choice == "s":
            snooze_until = datetime.now().strftime("%H:%M")
            print(f"Snoozed. (Re-run with a new alarm at +5 min if needed: currently {snooze_until})")
            # Minimal snooze: schedule a one-off alarm 5 minutes from now.
            alarms = load_alarms()
            snooze_time = (datetime.now().timestamp() + 5 * 60)
            snooze_hhmm = datetime.fromtimestamp(snooze_time).strftime("%H:%M")
            alarms.append(Alarm(id=next_id(alarms), time=snooze_hhmm, label=f"(snoozed) {alarm.label}".strip()))
            save_alarms(alarms)
            print(f"New snooze alarm set for {snooze_hhmm}.")
            return
        elif choice == "":
            print("Dismissed.")
            return


def cmd_start(_args: argparse.Namespace) -> None:
    print(f"Monitoring alarms from {STORE_PATH}. Press Ctrl+C to stop.")
    try:
        while True:
            alarms = load_alarms()
            now = datetime.now()
            now_hhmm = now.strftime("%H:%M")
            today = now.strftime("%Y-%m-%d")
            changed = False

            for alarm in alarms:
                if not alarm.enabled:
                    continue
                if alarm.time != now_hhmm:
                    continue
                if alarm.last_fired_date == today:
                    continue  # already fired this minute/day

                ring(alarm)
                alarm.last_fired_date = today
                if not alarm.repeat_daily:
                    alarm.enabled = False
                changed = True

            if changed:
                save_alarms(alarms)

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped monitoring.")


# --------------------------------------------------------------------------
# CLI wiring
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alarm_clock.py",
        description="A simple command-line alarm clock.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a new alarm")
    p_add.add_argument("time", type=parse_time_str, help="Time in 24-hour HH:MM format, e.g. 07:30")
    p_add.add_argument("--label", help="Optional label, e.g. 'Wake up'")
    p_add.add_argument("--repeat", action="store_true", help="Repeat this alarm every day")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List all alarms")
    p_list.set_defaults(func=cmd_list)

    p_remove = sub.add_parser("remove", help="Remove an alarm by id")
    p_remove.add_argument("id", type=int)
    p_remove.set_defaults(func=cmd_remove)

    p_start = sub.add_parser("start", help="Start monitoring alarms (blocks until Ctrl+C)")
    p_start.set_defaults(func=cmd_start)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()