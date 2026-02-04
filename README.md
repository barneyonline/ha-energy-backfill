# ha-energy-backfill

Home Assistant blueprint to reconcile delayed energy reporting from devices that report daily energy by converting it into a lifetime counter and importing backdated statistics for a proper energy sensor while tracking active cycles.

## What it does
- Tracks active cycles based on status changes and stores cycle durations for the day.
- On "energy yesterday" update, backfills lifetime kWh once per day, imports a backdated statistics sample for an energy sensor, and resets daily trackers.
- Ignores the first "energy yesterday" reading if no cycle times have been recorded yet.
- Splits cycles that cross midnight so yesterday's energy is attributed to the correct day.
- Also runs hourly and on Home Assistant startup to catch missed daily updates, but only processes after the energy-yesterday sensor updates since midnight.

## Requirements
- Home Assistant with the [Spook](https://spook.boo/) custom integration installed (provides the `recorder.import_statistics` service).
- Recorder enabled (default) and permission to import statistics.
- A proper energy sensor (`state_class: total_increasing`, `device_class: energy`, unit `kWh`) to receive the backfilled statistics.
- Caution: importing statistics can permanently skew your history if configured incorrectly. See the [Spook recorder docs](https://spook.boo/recorder/).

## Import
1. Copy `blueprints/automation/energy_backfill.yaml` to your Home Assistant config at `config/blueprints/automation/energy_backfill.yaml`, or import by URL:
   `https://raw.githubusercontent.com/barneyonline/ha-energy-backfill/main/blueprints/automation/energy_backfill.yaml`
2. In Home Assistant: Settings -> Automations & Scenes -> Blueprints -> Create Automation, then select "Energy Backfill".

## Setup
1. Install Spook and restart Home Assistant.
2. Import the blueprint (local file or URL).
3. Create the helpers listed below in the Home Assistant UI:
   - Settings -> Devices & Services -> Helpers -> Create Helper.
   - Choose the helper type (Number, Date & Time, or Text) and apply the suggested defaults below.
   - Repeat for each helper, giving each a clear name and entity ID.
4. Create or choose a proper energy sensor to receive backfilled statistics (details below).
5. Create an automation from the blueprint and select your entities/helpers.
6. Review your status sensor's possible states in Developer Tools -> States; add any additional inactive values to `inactive_states`.
7. Save and enable the automation.

## Configuration (Blueprint inputs)
- `energy_yesterday_sensor`: sensor reporting yesterday's energy.
- `energy_yesterday_unit`: unit for the energy yesterday sensor (Wh or kWh).
- `status_sensor`: status sensor used to detect active vs inactive states.
- `lifetime_energy_helper`: input_number storing cumulative kWh.
- `lifetime_energy_statistic_id`: entity ID of a proper energy sensor to import statistics for (required).
- `cycle_start_helper`: input_datetime tracking the current cycle start. The blueprint clears it to the Unix epoch (timestamp 0) when idle.
- `daily_active_seconds_helper`: input_number storing total active seconds for the current day.
- `cycle_durations_helper`: input_text containing a JSON array of cycle durations in seconds (initialize to `[]`).
- `last_processed_date_helper`: input_text storing the last processed date in YYYY-MM-DD (initialize to empty).
- `inactive_states`: list of state strings treated as inactive (default: `off`, `unavailable`, `unknown`).

## Helpers to create (suggested defaults)
- `input_number`: lifetime energy (kWh), min 0, max large (for example 100000), step 0.001.
- `input_datetime`: cycle start, date + time, initial blank.
- `input_number`: daily active seconds, min 0, max 90000, step 1, initial 0.
- `input_text`: cycle durations JSON, initial `[]`.
- `input_text`: last processed date, initial empty string.

## Required energy sensor
The blueprint always imports backdated statistics, so you must supply a proper energy sensor
(state_class `total_increasing`, device_class `energy`, unit `kWh`) and set its entity ID as
`lifetime_energy_statistic_id`. The blueprint imports a statistic at today's midnight with the
updated total so yesterday's usage is attributed correctly.
If you already have a compatible energy sensor, use it; otherwise create one using the template
sensor example below.

## Example configuration
```yaml
automation:
  - alias: "LG ThinQ Lifetime Energy"
    use_blueprint:
      path: energy_backfill.yaml
      input:
        energy_yesterday_sensor: sensor.lg_washer_energy_yesterday
        energy_yesterday_unit: Wh
        status_sensor: sensor.lg_washer_status
        lifetime_energy_helper: input_number.lg_washer_lifetime_energy
        lifetime_energy_statistic_id: sensor.lg_washer_lifetime_energy
        cycle_start_helper: input_datetime.lg_washer_cycle_start
        daily_active_seconds_helper: input_number.lg_washer_daily_active_seconds
        cycle_durations_helper: input_text.lg_washer_cycle_durations
        last_processed_date_helper: input_text.lg_washer_last_energy_date
        inactive_states:
          - off
          - unavailable
          - unknown
```

## Energy sensor example (required)
If you do not already have a total-increasing energy sensor, add a template sensor like this and
reload Template Entities (or restart Home Assistant). Use the resulting entity ID as
`lifetime_energy_statistic_id`.
```yaml
template:
  - sensor:
      - name: "LG Washer Lifetime Energy"
        unit_of_measurement: "kWh"
        device_class: energy
        state_class: total_increasing
        state: "{{ states('input_number.lg_washer_lifetime_energy') }}"
```
