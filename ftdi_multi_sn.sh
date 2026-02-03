#!/bin/bash

# Please download cd_ftdi_buttons_v* to CD from go/challengerdeep-ftdi-control
# FTDI_PATH
methods_and_descriptions=(
  "list"                      "List all support methods"
  "power_on"                  "power on PMIC"
  "soc_wreset"                "Warm Reset to SoC"
  "soc_creset"                "Cold SOC_Reset to SoC"
  "crashdump"                 "Trigger Crashdump"
  "creset_rom_recovery"       "SOC Cold Reset + Enter into ROM Recovery"
  "creset_ufs_boot"           "SOC Cold Reset + UFS Boot"
  "creset_sd_boot"            "SoC Cold Reset + Enter into SD Card boot"
  "creset_fastboot"           "Soc Cold Reset + Enter into Bootloader Fastboot"
  "master_disconnect"         "Power off PMIC"
  "board_on"                  "Power on board"
  "board_off"                 "Power off board"
)
LENGTH=$(( ${#methods_and_descriptions[@]} / 2 ))

function list_commands() {
  echo "Support commands："
  printf "%-4s %-20s %s\n" "ID" "Command" "Description"
  for ((id = 0; id < LENGTH; id++)); do
    index=id*2
    command="${methods_and_descriptions[$index]}"
    description="${methods_and_descriptions[$index+1]}"
    printf "%-4d %-20s %s\n" "$id" "$command" "$description"
  done
}

function validate_input() {
  local command_id="$1"
  # Delay check removed since it is no longer an input

  if [[ -z $command_id || $command_id -eq 0 ]]; then
    list_commands
    return 1
  fi

  if [[ ! ${command_id} =~ ^[0-9]+$ ]]; then
    echo "**** Invalid Input: Command ID ${command_id} is not a number."
    return 1
  fi

  if ((command_id >= LENGTH)); then
    echo "**** Invalid Command ID: ${command_id}"
    list_commands
    return 1
  fi

  return 0
}

while true; do
  if [[ -z $FTDI_PATH ]]; then
    echo "**** Please set up your FTDI_PATH env variable to point to sc_ftdi_buttons."
    break
  elif [[ ! -e $FTDI_PATH ]]; then
    echo "**** FTDI_PATH is invalid"
    break
  fi

  # --- MODIFIED ARGUMENT PARSING START ---
  if [[ -z $1 ]] || [[ $retry -eq 1 ]]; then
    echo "Usage: <ID> [<Serial Number>]"
    # Read ID and Serial Number from interactive prompt
    read -p "Input Command ID (0 <= ID < ${LENGTH})：" command_id serial_number
  else
    command_id=$1
    
    # Check 2nd Argument (Serial Number)
    if [[ -n $2 ]]; then
      serial_number=$2
    fi
    
    retry=1
  fi

  # Hardcode delay to 0 to preserve logic (no delay)
  delay=0
  # --- MODIFIED ARGUMENT PARSING END ---

  if ! validate_input "$command_id"; then
    continue
  fi

  # --- LOGIC CHANGE: ONLY AUTO-DETECT IF SN IS MISSING ---
  if [[ -z $serial_number ]]; then
      serial_number=$(lsusb -d 0403:6011 -v | awk '/iSerial/ {print $3}' | awk 'NR==1{print}' | awk -F'_' '{print $1}')
  fi
  # -------------------------------------------------------

  if [[ -z $serial_number ]]; then
    echo "SN doesn't exist"
  else
    echo "SN=${serial_number}"
  fi

  method="${methods_and_descriptions[command_id * 2]}"
  method_cmd="-m ${method}"
  
  # Delay is 0, so this block will be skipped, but kept for logic preservation
  if ((delay > 0)); then
    delay_cmd="--delay ${delay}"
  else
    delay_cmd=""
  fi

  execute_command="${FTDI_PATH} --sn ${serial_number} ${method_cmd} ${delay_cmd}"
  echo "${execute_command}"
  ${execute_command}
  break
done
