# Testing Harness

This repository includes a small REST API test harness for exercising the
Energy Backfill blueprint without waiting for real device cycles.

## Prerequisites
- A running Home Assistant instance.
- A long-lived access token.
- A test automation created from the blueprint and pointed at test entities.

Set environment variables:
```bash
export HA_BASE_URL=http://homeassistant.local:8123
export HA_TOKEN=YOUR_LONG_LIVED_TOKEN
```

## Suggested test entities (defaults)
The script defaults to these entity IDs. Create them as helpers or template
entities so you can control them easily:

- `sensor.test_energy_yesterday` (energy sensor input for the automation)
- `input_select.test_status` (status entity for active/inactive)
- `input_number.test_lifetime_energy`
- `input_datetime.test_cycle_start`
- `input_number.test_daily_active_seconds`
- `input_text.test_cycle_durations`
- `input_text.test_last_processed_date`

If your energy input must be writable, create:
- `input_number.test_energy_yesterday` and a template sensor
  `sensor.test_energy_yesterday` that mirrors it.

Then run commands with:
```bash
--energy-write-entity input_number.test_energy_yesterday
```

## Usage
Initialize helpers:
```bash
python3 scripts/ha_test_harness.py init
```

Start a cycle:
```bash
python3 scripts/ha_test_harness.py start
```

End a cycle (simulate 20 minutes duration):
```bash
python3 scripts/ha_test_harness.py end --duration-sec 1200
```

Trigger the energy update:
```bash
python3 scripts/ha_test_harness.py energy --energy-wh 850
```

Simulate a cycle that crosses midnight and trigger energy:
```bash
python3 scripts/ha_test_harness.py split --energy-wh 900
```

Run a full scenario (init -> cycle -> energy):
```bash
python3 ha_test_harness.py scenario --energy-wh 850 --duration-sec 1200 --init
```

Dump current test entity states:
```bash
python3 scripts/ha_test_harness.py dump
```

## Notes
- The automation only triggers on state changes. Use a new `--energy-wh` value
  each time to ensure the update fires.
- To force a re-run for the same day, clear `input_text.test_last_processed_date`.
- The script uses Home Assistant's REST API and can set state for any entity
  ID, but using helpers is safer and easier to reason about.
