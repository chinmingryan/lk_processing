#!/bin/bash

set -ex
set -o pipefail

# 1. Set Defaults
# Default path is the directory where this script lives
DEFAULT_PATH=$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)
FLASH_PACK_PATH=${FLASH_PACK_PATH:-$DEFAULT_PATH}
SERIAL=${USB_BOOT_SERIAL} # Default from env var if set

# 2. Parse Arguments (Supports -p/--path and -s/--serial)
while [[ $# -gt 0 ]]; do
  case $1 in
    -p|--path)
      FLASH_PACK_PATH="$2"
      shift 2
      ;;
    -s|--serial)
      SERIAL="$2"
      shift 2
      ;;
    *)
      # Fallback: If a naked argument is provided, treat it as the SERIAL
      # (Preserves backward compatibility: ./script.sh <SERIAL>)
      if [[ -z "$SERIAL" ]] && [[ ! "$1" =~ ^- ]]; then
          SERIAL="$1"
      fi
      shift
      ;;
  esac
done

# 3. Configure Serial Flag
# Initialize serial flag; leave empty if no serial is provided
SERIAL_FLAG=""
if [[ -n "$SERIAL" ]]; then
  SERIAL_FLAG="-s $SERIAL"
fi

echo "Using Flash Pack Path: ${FLASH_PACK_PATH}"
echo "Targeting Serial: ${SERIAL:-"Auto-detect"}"

# 4. Execute the recovery tool
# Note: We now use ${FLASH_PACK_PATH} for both the python script and the binaries
python3 "${FLASH_PACK_PATH}/pixel_fastboot_recovery.py" \
    $SERIAL_FLAG \
    -i "${FLASH_PACK_PATH}/binaries/usb_booting.json" \
    --fastboot=${FASTBOOT:-fastboot} \
    -v
