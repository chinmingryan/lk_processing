# MBU Batch Test Automation

**Main Script:** `send_to_terminal_batch_v2.py`
**Author:** Chin Ming Ryan Wong

## Overview
The MBU Batch Test Automation tool is a multi-threaded framework designed to execute hardware validation test plans across multiple MBU devices simultaneously.

It automates the full lifecycle of a test iteration:
1.  **Device Setup:** Pairs SoC and Board serial numbers and handles ROM Recovery/LK Staging.
2.  **Execution:** Connects via `dhub`, routes commands to specific UART ports (APC, AOSS, A32), and executes Fastboot commands.
3.  **Reporting:** Captures logs and generates pass/fail summaries.

## Features
* **Parallel Execution:** Uses Python threading to run test plans on all connected pairs found in `paired_serial_numbers.txt`.
* **Smart Command Routing:** Automatically detects command prefixes in the test plan to route instructions to the correct subsystem:
    * **APC:** Default terminal.
    * **AOSS:** Commands prefixed with `AOSS_SENSOR_CORE:`.
    * **AOSS A32:** Commands prefixed with `AOSS_A32 uart:`.
* **Automated Recovery:** Handles `<reboot device>` commands by triggering a hardware reset and re-staging LK.
* **Fastboot Support:** automatically resolves paths for ramdisk images (files ending in `.ext2`) relative to the flash package.

## Prerequisites

### Dependencies
Ensure the following are in your `PYTHONPATH` or the script directory:
* `pyserial`
* `dhub` (Google internal tool)
* **Custom Modules:** `dhub_automation`, `serial_num_util`, `getSummary`, `constants`, `send_to_terminal`.

### System Requirements
* **Linux Environment:** The script utilizes `sudo`, `chown`, and Linux-specific device paths (`/dev/bus/usb`).
* **Root Privileges:** Required to control FTDI/GPIO and manage log file permissions.

## Configuration (Important)

**⚠️ Action Required:** This codebase uses a `constants.py` file with hardcoded paths. You **must** update these to match your local environment before running.

Open `constants.py` and update the following:
* **`LOG_OUTPUT_DIR`**: Directory where raw logs and summaries will be saved.
* **`OUTPUT_ZIP_DIR`**: Directory for archived logs.
* **`FTDI_MULTI_PATH`**: Path to the `ftdi_multi_sn.sh` script.
* **`STAGE_LK_PATH`**: Path to the `stage_for_lk_multi_sn.sh` script.

*Note: The script currently attempts to `chown` logs to user `chinmingryan`. Update the user in `send_to_terminal_batch_v2.py` (lines 115, 120) or remove the `subprocess.run` calls.*

## Usage

Run the script with `sudo` permissions.

```bash
sudo python3 send_to_terminal_batch_v2.py \
  -t ./test_plans/stress_test.csv \
  -k ./flash_packs/latest_build \
  -i 50
```
## Arguments
| Flag | Long Flag | Default | Description |
|---|---|---|---|
| -t | --test_plan | ../mbu_b0_ebu_cpu_c2.csv | Path to the CSV test plan |
| -k | --lk_package_path | ../mbu_b0_v5p2_ebu | Path to the LK flash package (containing ramdisks). |
| -i | --iteration | 10 | number of test loops to execute. |

## Device Paring
The script relies on ```serial_num_util.py``` to map Board Serial Numbers (FTDI) to SoC Serial Numbers (Fastboot).

**First Run:** It will automatically generate paired_serial_numbers.txt by toggling devices one by one (Blink Test).

**Subsequent Runs:** It reads from the file to save time.

**Reset:** Delete paired_serial_numbers.txt to force a re-scan.