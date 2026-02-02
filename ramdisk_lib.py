#!/usr/bin/env python3
# Author: Chin Ming Ryan Wong

from get_test_commands import getTestCommands
import os
import subprocess
import time

def check_reboot_req(ip):
    tc_dict = getTestCommands(ip)
    for testType in tc_dict[ip]:
        if testType.get("TestType") == "reboot": return True
        else: return False

def find_ramdisk(ip: str) -> str or int:
    """
    Searches through the command list for a given IP to find the ramdisk filename.

    Args:
        ip (str): The name of the IP to search for (e.g., 'aoss_ambss').

    Returns:
        str: The filename of the ramdisk (e.g., 'ramdisk-aoss.ext2') if found.
        int: Returns 0 if no ramdisk file is found for that IP.
    """
    tc_dict = getTestCommands(ip)

    # First, check if the IP key exists in the dictionary
    if ip not in tc_dict:
        return 0

    # Loop through the list of command dictionaries for the given IP
    for command_info in tc_dict[ip]:
        testType = command_info.get("TestType")
        command = command_info.get("Command")

        # Check if it's a fastboot command AND contains '.ext2'
        if testType == "fastboot" and ".ext2" in command:
            
            # 1. Isolate the file path from the command string
            #    split() turns "fastboot stage path/file" into ['fastboot', 'stage', 'path/file']
            #    [-1] gets the last element, which is the path.
            file_path = command.split()[-1]
            
            # 2. Use os.path.basename to reliably get the filename from the path
            filename = os.path.basename(file_path)
            
            # 3. Return the found filename
            return filename
            
    # If the loop finishes without finding any fastboot command with a ramdisk, return 0
    return 0

def mount_ramdisk(ramdisk,dir):
    subprocess.run(['fastboot', 'oem', 'ramdisk', 'unmount'])
    if subprocess.run(['fastboot', 'oem', 'ramdisk', 'setup_stage']).returncode == 1:
        print("Failed detected!")
        return 1
    ramdisk_path = os.path.join(dir, ramdisk)
    if subprocess.run(['fastboot', 'stage', ramdisk_path]).returncode == 1: return 1
    if subprocess.run(['fastboot', 'oem', 'ramdisk', 'mount']).returncode == 1: return 1
    time.sleep(1)
    return 0
    

if __name__ == '__main__':
    ip = "gpca"
    if check_reboot_req(ip):
        print("Reboot required")
    print(find_ramdisk(ip))