#!/usr/bin/env python3
"""
Minimal test harness for the Energy Backfill blueprint using the HA REST API.

Examples:
  HA_BASE_URL=http://homeassistant.local:8123 HA_TOKEN=... \
    python3 scripts/ha_test_harness.py init

  HA_BASE_URL=http://homeassistant.local:8123 HA_TOKEN=... \
    python3 scripts/ha_test_harness.py start

  HA_BASE_URL=http://homeassistant.local:8123 HA_TOKEN=... \
    python3 scripts/ha_test_harness.py end --duration-sec 1800

  HA_BASE_URL=http://homeassistant.local:8123 HA_TOKEN=... \
    python3 scripts/ha_test_harness.py energy --energy-wh 750

  HA_BASE_URL=http://homeassistant.local:8123 HA_TOKEN=... \
    python3 scripts/ha_test_harness.py split --energy-wh 900
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from urllib import error, request


DEFAULTS = {
    "energy_sensor": "sensor.test_energy_yesterday",
    "status_entity": "input_select.test_status",
    "lifetime_helper": "input_number.test_lifetime_energy",
    "cycle_start_helper": "input_datetime.test_cycle_start",
    "daily_active_helper": "input_number.test_daily_active_seconds",
    "durations_helper": "input_text.test_cycle_durations",
    "last_processed_helper": "input_text.test_last_processed_date",
    "active_state": "running",
    "inactive_state": "off",
}


def _require(value: str | None, label: str) -> str:
    if value:
        return value
    print(f"Missing required value: {label}", file=sys.stderr)
    sys.exit(2)


def _base_url(args) -> str:
    return _require(args.base_url, "HA_BASE_URL or --base-url")


def _token(args) -> str:
    return _require(args.token, "HA_TOKEN or --token")


def _request(args, method: str, path: str, payload: dict | None = None):
    url = _base_url(args).rstrip("/") + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_token(args)}")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            if not body:
                return None
            return json.loads(body.decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc


def _domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


def _call_service(args, domain: str, service: str, data: dict):
    return _request(args, "POST", f"/api/services/{domain}/{service}", data)


def _set_state(args, entity_id: str, state, attributes: dict | None = None):
    payload = {"state": str(state)}
    if attributes:
        payload["attributes"] = attributes
    return _request(args, "POST", f"/api/states/{entity_id}", payload)


def _set_input_number(args, entity_id: str, value: float):
    return _call_service(
        args, "input_number", "set_value", {"entity_id": entity_id, "value": value}
    )


def _set_input_text(args, entity_id: str, value: str):
    return _call_service(
        args, "input_text", "set_value", {"entity_id": entity_id, "value": value}
    )


def _set_input_select(args, entity_id: str, value: str):
    return _call_service(
        args, "input_select", "select_option", {"entity_id": entity_id, "option": value}
    )


def _set_input_boolean(args, entity_id: str, value: str):
    service = "turn_on" if value.lower() in {"on", "true", "1"} else "turn_off"
    return _call_service(args, "input_boolean", service, {"entity_id": entity_id})


def _set_by_domain(args, entity_id: str, value):
    domain = _domain(entity_id)
    if domain == "input_number":
        return _set_input_number(args, entity_id, float(value))
    if domain == "input_text":
        return _set_input_text(args, entity_id, str(value))
    if domain == "input_select":
        return _set_input_select(args, entity_id, str(value))
    if domain == "input_boolean":
        return _set_input_boolean(args, entity_id, str(value))
    return _set_state(args, entity_id, value)


def _get_state(args, entity_id: str):
    return _request(args, "GET", f"/api/states/{entity_id}")


def _parse_start_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid --start-iso value: {value}") from exc


def _local_midnight(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _timestamp(dt: datetime) -> int:
    return int(dt.timestamp())


def _init_helpers(args, energy_wh: float | None):
    _set_input_number(args, args.lifetime_helper, 0)
    _set_input_number(args, args.daily_active_helper, 0)
    _set_input_text(args, args.durations_helper, "[]")
    _set_input_text(args, args.last_processed_helper, "")
    _call_service(
        args,
        "input_datetime",
        "set_datetime",
        {"entity_id": args.cycle_start_helper, "timestamp": 0},
    )
    _set_by_domain(args, args.status_entity, args.inactive_state)
    if energy_wh is not None:
        _set_by_domain(args, args.energy_write_entity, energy_wh)


def cmd_init(args):
    _init_helpers(args, args.energy_wh)
    print("Initialized helpers and set status to inactive.")


def cmd_start(args):
    _set_by_domain(args, args.status_entity, args.active_state)
    print(f"Set status to {args.active_state}.")


def cmd_end(args):
    if args.duration_sec is not None:
        start = datetime.now() - timedelta(seconds=args.duration_sec)
        _call_service(
            args,
            "input_datetime",
            "set_datetime",
            {"entity_id": args.cycle_start_helper, "timestamp": _timestamp(start)},
        )
    _set_by_domain(args, args.status_entity, args.inactive_state)
    print(f"Set status to {args.inactive_state}.")


def cmd_energy(args):
    _set_by_domain(args, args.energy_write_entity, args.energy_wh)
    print(f"Set energy to {args.energy_wh} Wh.")


def cmd_split(args):
    now = datetime.now()
    if args.start_iso:
        start = _parse_start_iso(args.start_iso)
    else:
        start = _local_midnight(now) - timedelta(minutes=10)
    _call_service(
        args,
        "input_datetime",
        "set_datetime",
        {"entity_id": args.cycle_start_helper, "timestamp": _timestamp(start)},
    )
    _set_by_domain(args, args.status_entity, args.active_state)
    _set_by_domain(args, args.energy_write_entity, args.energy_wh)
    print("Set a pre-midnight start, set status active, and updated energy.")


def cmd_scenario(args):
    if args.init:
        _init_helpers(args, 0)
    if args.start_iso:
        start = _parse_start_iso(args.start_iso)
    else:
        start = datetime.now() - timedelta(seconds=args.duration_sec)
    _call_service(
        args,
        "input_datetime",
        "set_datetime",
        {"entity_id": args.cycle_start_helper, "timestamp": _timestamp(start)},
    )
    _set_by_domain(args, args.status_entity, args.active_state)
    _set_by_domain(args, args.status_entity, args.inactive_state)
    _set_by_domain(args, args.energy_write_entity, args.energy_wh)
    print("Ran scenario: start -> end -> energy update.")


def cmd_dump(args):
    entities = [
        args.energy_sensor,
        args.status_entity,
        args.lifetime_helper,
        args.cycle_start_helper,
        args.daily_active_helper,
        args.durations_helper,
        args.last_processed_helper,
    ]
    for entity_id in entities:
        state = _get_state(args, entity_id)
        print(json.dumps(state, indent=2, sort_keys=True))


def _add_common_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--base-url", default=os.environ.get("HA_BASE_URL"), help="Home Assistant URL"
    )
    parser.add_argument(
        "--token", default=os.environ.get("HA_TOKEN"), help="Long-lived access token"
    )
    parser.add_argument(
        "--energy-sensor",
        default=os.environ.get("HA_ENERGY_SENSOR", DEFAULTS["energy_sensor"]),
        help="Energy yesterday sensor entity (automation input)",
    )
    parser.add_argument(
        "--energy-write-entity",
        default=os.environ.get("HA_ENERGY_WRITE_ENTITY"),
        help="Entity to write for energy updates (defaults to energy sensor)",
    )
    parser.add_argument(
        "--status-entity",
        default=os.environ.get("HA_STATUS_ENTITY", DEFAULTS["status_entity"]),
        help="Status entity for active/inactive changes",
    )
    parser.add_argument(
        "--lifetime-helper",
        default=os.environ.get("HA_LIFETIME_HELPER", DEFAULTS["lifetime_helper"]),
        help="input_number for lifetime kWh",
    )
    parser.add_argument(
        "--cycle-start-helper",
        default=os.environ.get("HA_CYCLE_START_HELPER", DEFAULTS["cycle_start_helper"]),
        help="input_datetime for cycle start",
    )
    parser.add_argument(
        "--daily-active-helper",
        default=os.environ.get(
            "HA_DAILY_ACTIVE_HELPER", DEFAULTS["daily_active_helper"]
        ),
        help="input_number for daily active seconds",
    )
    parser.add_argument(
        "--durations-helper",
        default=os.environ.get("HA_DURATIONS_HELPER", DEFAULTS["durations_helper"]),
        help="input_text for JSON durations",
    )
    parser.add_argument(
        "--last-processed-helper",
        default=os.environ.get(
            "HA_LAST_PROCESSED_HELPER", DEFAULTS["last_processed_helper"]
        ),
        help="input_text for last processed date",
    )
    parser.add_argument(
        "--active-state",
        default=os.environ.get("HA_ACTIVE_STATE", DEFAULTS["active_state"]),
        help="State treated as active",
    )
    parser.add_argument(
        "--inactive-state",
        default=os.environ.get("HA_INACTIVE_STATE", DEFAULTS["inactive_state"]),
        help="State treated as inactive",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Energy Backfill test harness (Home Assistant REST API)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_init = subparsers.add_parser("init", help="Reset helpers to a clean state")
    _add_common_args(parser_init)
    parser_init.add_argument("--energy-wh", type=float, default=0)
    parser_init.set_defaults(func=cmd_init)

    parser_start = subparsers.add_parser("start", help="Start a cycle")
    _add_common_args(parser_start)
    parser_start.set_defaults(func=cmd_start)

    parser_end = subparsers.add_parser("end", help="End a cycle")
    _add_common_args(parser_end)
    parser_end.add_argument("--duration-sec", type=int)
    parser_end.set_defaults(func=cmd_end)

    parser_energy = subparsers.add_parser(
        "energy", help="Update the energy-yesterday sensor"
    )
    _add_common_args(parser_energy)
    parser_energy.add_argument("--energy-wh", type=float, required=True)
    parser_energy.set_defaults(func=cmd_energy)

    parser_split = subparsers.add_parser(
        "split",
        help="Simulate a cycle that crosses midnight and trigger energy update",
    )
    _add_common_args(parser_split)
    parser_split.add_argument("--energy-wh", type=float, required=True)
    parser_split.add_argument(
        "--start-iso",
        help="ISO start time (defaults to yesterday 23:50 local time)",
    )
    parser_split.set_defaults(func=cmd_split)

    parser_scenario = subparsers.add_parser(
        "scenario", help="Run a basic cycle + energy update scenario"
    )
    _add_common_args(parser_scenario)
    parser_scenario.add_argument("--energy-wh", type=float, required=True)
    parser_scenario.add_argument(
        "--duration-sec",
        type=int,
        default=1800,
        help="Duration for the simulated cycle (default: 1800)",
    )
    parser_scenario.add_argument(
        "--start-iso",
        help="ISO start time (overrides --duration-sec)",
    )
    parser_scenario.add_argument(
        "--init",
        action="store_true",
        help="Reset helpers before running the scenario",
    )
    parser_scenario.set_defaults(func=cmd_scenario)

    parser_dump = subparsers.add_parser("dump", help="Dump test entity states")
    _add_common_args(parser_dump)
    parser_dump.set_defaults(func=cmd_dump)

    args = parser.parse_args()
    if not args.energy_write_entity:
        args.energy_write_entity = args.energy_sensor

    try:
        args.func(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
