# Battery Doctor

A Python-based battery optimizer for Termux.

## Features

*   **Health Diagnostics**: Calculates battery health, estimates charging cycles, and detects harmful charging habits.
*   **Real-time Monitoring**: A dashboard showing capacity, cycles, status, temperature, and health.
*   **Optimization**: Smart charging alarms, discharge calibration, and a background app killer.
*   **Usage Analytics**: Tracks screen-on time, app consumption, and charging history.
*   **Maintenance System**: Provides scheduled optimizations and health tips.
*   **Termux Integration**: Uses `termux-battery-status` and `termux-job-scheduler`.

## Dependencies

*   `psutil`: For getting system information.
*   `matplotlib`: For generating graphs.
*   `termux-api`: For accessing Termux-specific features.

To install the dependencies, run:

```bash
pip install psutil matplotlib
pkg install termux-api
```

## Usage

```bash
python battery_doctor.py monitor
python battery_doctor.py calibrate
python battery_doctor.py report --days 30
```
