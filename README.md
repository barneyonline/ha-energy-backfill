# ha-energy-backfill

Home Assistant blueprint to reconcile delayed energy reporting from devices that report daily energy by converting it into a lifetime counter while tracking active cycles.

## What it does
- Tracks active cycles based on status changes and stores cycle durations for the day.
- On "energy yesterday" update, backfills lifetime kWh once per day and resets daily trackers.
- Splits cycles that cross midnight so yesterday's energy is attributed to the correct day.

## Import
1. Copy `blueprints/automation/energy_backfill.yaml` to your Home Assistant config at `config/blueprints/automation/energy_backfill.yaml`, or import by URL:
   `https://raw.githubusercontent.com/barneyonline/ha-energy-backfill/main/blueprints/automation/energy_backfill.yaml`
2. In Home Assistant: Settings -> Automations & Scenes -> Blueprints -> Create Automation, then select "Energy Backfill".

## Setup
1. Import the blueprint (local file or URL).
2. Create the helpers listed below in the Home Assistant UI:
   - Settings -> Devices & Services -> Helpers -> Create Helper.
   - Choose the helper type (Number, Date & Time, or Text) and apply the suggested defaults below.
   - Repeat for each helper, giving each a clear name and entity ID.
3. Create an automation from the blueprint and select your entities/helpers.
4. Review your status sensor's possible states in Developer Tools -> States; add any additional inactive values to `inactive_states`.
5. Save and enable the automation.

## Configuration (Blueprint inputs)
- `energy_yesterday_sensor`: sensor reporting yesterday's energy in Wh.
- `status_sensor`: status sensor used to detect active vs inactive states.
- `lifetime_energy_helper`: input_number storing cumulative kWh.
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

## Example configuration
```yaml
automation:
  - alias: "LG ThinQ Lifetime Energy"
    use_blueprint:
      path: energy_backfill.yaml
      input:
        energy_yesterday_sensor: sensor.lg_washer_energy_yesterday
        status_sensor: sensor.lg_washer_status
        lifetime_energy_helper: input_number.lg_washer_lifetime_energy
        cycle_start_helper: input_datetime.lg_washer_cycle_start
        daily_active_seconds_helper: input_number.lg_washer_daily_active_seconds
        cycle_durations_helper: input_text.lg_washer_cycle_durations
        last_processed_date_helper: input_text.lg_washer_last_energy_date
        inactive_states:
          - off
          - unavailable
          - unknown
```

## Optional template sensor
```yaml
template:
  - sensor:
      - name: "LG Washer Lifetime Energy"
        unit_of_measurement: "kWh"
        device_class: energy
        state_class: total_increasing
        state: "{{ states('input_number.lg_washer_lifetime_energy') }}"
```
