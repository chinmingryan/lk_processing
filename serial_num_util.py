#!/usr/bin/env python3
# Author: Chin Ming Ryan Wong

import subprocess, time, os, argparse
from constants import FTDI_MULTI_PATH, SN_PAIR_FILE, STAGE_LK_PATH

def creset_and_lk(package_path, soc_sn = None, brd_sn = None):
    print(f"C-Resetting device with SoC SN: {soc_sn} and Board SN: {brd_sn}")
    failCount = 0
    reboot = False
    # Try up to 5 times to recover and stage LK
    while failCount < 5 and not reboot:
        print(f"Attempting ROM Recovery")
        if brd_sn == None:
            subprocess.run(['sudo', FTDI_MULTI_PATH, '5'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(['sudo', FTDI_MULTI_PATH, '5', brd_sn], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Re-staging {brd_sn} for lk")
        if soc_sn == None:
            cmd = f"{STAGE_LK_PATH} --path {package_path}"
        else:
            cmd = f"{STAGE_LK_PATH} --path {package_path} --serial {soc_sn}"
        output = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if output.returncode != 0: failCount += 1
        else:
            # print("LK loaded")
            reboot = True
    time.sleep(5)

def get_brd_serial_num():
    cmd = "lsusb -d 0403:6011 -v | awk '/iSerial/ {print $3}' | awk -F'_' '{print $1}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Get the list of serials
    if result.returncode == 0:
        serial_list = result.stdout.strip().split('\n')
        serial_list = list(dict.fromkeys(serial_list))
        return serial_list
    else:
        print(f"Error: {result.stderr}")
        return 1

def get_soc_serial_num():
    serial_num = subprocess.run(["fastboot","devices"], capture_output=True, text=True).stdout.split()[::3]
    return serial_num

def get_fastboot_devices_with_mode():
    """
    Returns a list of dictionaries containing 'sn' and 'mode'.
    Example return: [{'sn': '8832...', 'mode': 'ROM Recovery'}, {'sn': '73a3...', 'mode': 'fastboot'}]
    """
    device_list = []
    
    try:
        # Run 'fastboot devices' and capture output
        result = subprocess.run(["fastboot", "devices"], capture_output=True, text=True)
        
        # Process each line
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().splitlines()
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    # parts[0] is always the Serial Number
                    sn = parts[0]
                    
                    # parts[1:] contains the mode (e.g., ['fastboot'] or ['ROM', 'Recovery'])
                    # We join them back together to handle spaces in "ROM Recovery"
                    mode = " ".join(parts[1:])
                    
                    device_list.append({'sn': sn, 'mode': mode})
                    
    except FileNotFoundError:
        print("Error: 'fastboot' tool not found in PATH.")

    return device_list

def get_paired_sn():
    brd_sn_list = get_brd_serial_num()
    soc_sn_list = get_soc_serial_num()
    if len(brd_sn_list) != len(soc_sn_list):
        print("Warning: Mismatch in number of board and SoC serial numbers detected.")
        return []
    
    # Set all SoC to Rom Recovery Mode
    for brd_sn in brd_sn_list:
        subprocess.run(['sudo', FTDI_MULTI_PATH, '5', brd_sn], stdout=subprocess.DEVNULL)

    ref_devices = get_fastboot_devices_with_mode()
    sn_pairs = []
    
    # Blink test to identify pairing
    for brd_sn in brd_sn_list:
        # Change one SoC at a time to LK mode
        subprocess.run(['sudo', FTDI_MULTI_PATH, '8', brd_sn], stdout=subprocess.DEVNULL)
        cur_devices = get_fastboot_devices_with_mode()
        # Find the difference of current device mode from reference mode
        for device in cur_devices:
            if device not in ref_devices:
                print(f"Paired Board SN: {brd_sn} with SoC SN: {device['sn']}")
                # Add the paired serial numbers to the list
                sn_pairs.append({'brd_sn': brd_sn, 'soc_sn': device['sn']})
                # Update reference devices for next iteration
                ref_devices = cur_devices
                break
            # else continue checking next device
    return sn_pairs

def store_sn_list_to_file(sn_pairs, filepath=SN_PAIR_FILE):
    with open(filepath, 'w') as f:
        for pair in sn_pairs:
            f.write(f"Board SN: {pair['brd_sn']}, SoC SN: {pair['soc_sn']}\n")
    print(f"Paired serial numbers saved to {filepath}")

def retrieve_sn_list_from_file(filepath=SN_PAIR_FILE):
    sn_pairs = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                brd_sn = parts[0].split(': ')[1]
                soc_sn = parts[1].split(': ')[1]
                sn_pairs.append({'brd_sn': brd_sn, 'soc_sn': soc_sn})
        print(f"Paired serial numbers retrieved from {filepath}")
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
    return sn_pairs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate paired Board and SoC serial numbers.")
    parser.add_argument(
        "-lk",
        "--lk_package_path",
        type=str,
        help="Path to the directory containing the LK package.",
        default="/usr/local/google/home/chinmingryan/Documents/mbu_lk_related/flash_packs/mbu_b0_v5p2_ebu"
    )
    args = parser.parse_args()
    paired_sn = get_paired_sn()
    print(f"Generated serial number pairs: {paired_sn}")
    store_sn_list_to_file(paired_sn)
    print(f"Retrieved serial numbers from file: {retrieve_sn_list_from_file()}")
    for pair in paired_sn:
        creset_and_lk(args.lk_package_path, pair['soc_sn'], pair['brd_sn'])