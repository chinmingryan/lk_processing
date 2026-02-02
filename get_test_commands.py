#!/usr/bin/env python3
# Author: Chin Ming Ryan Wong

import csv
from collections import defaultdict
from pathvalidate import sanitize_filename
from constants import SUBSYSTEM_PATH, _CACHED_TEST_DATA

def getTestCommands(ip_name: str):
    """
    Loads test data for a specific IP from the CSV, returning a dictionary
    where the IP maps to a list of commands in their original order.
    """
    global _CACHED_TEST_DATA
    if _CACHED_TEST_DATA is None:
        _CACHED_TEST_DATA = _load_all_test_data()

    # Return the data for the specific IP requested
    # We sanitize the input ip_name to match the sanitized keys from the CSV
    sanitized_ip = sanitize_filename(ip_name.strip())
    if sanitized_ip in _CACHED_TEST_DATA:
        return {sanitized_ip: _CACHED_TEST_DATA[sanitized_ip]}
    return {}

def _load_all_test_data():
    """
    Reads the CSV and builds a dictionary mapping each IP to a
    list of command objects, preserving the original file order.
    """
    results = defaultdict(list)
    print("--- Loading and parsing test data from CSV... ---")
    
    try:
        with open(SUBSYSTEM_PATH, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                ip = sanitize_filename(row["IP"].strip())
                test_type = row["TestType"].strip()
                command = row["Command"].strip()
                slt_yn = row["Part of SLT (Y/N)"]
                if slt_yn == "Y":
                    if command and ip:
                        # Append a dictionary for each command. This preserves
                        # the TestType and, most importantly, the original order.
                        command_info = {
                            "TestType": test_type,
                            "Command": command
                        }
                        results[ip].append(command_info)
                        
                elif slt_yn == "N": continue

    except FileNotFoundError:
        print(f"ERROR: The file was not found at: {SUBSYSTEM_PATH}")
        return {}
    except KeyError as e:
        print(f"ERROR: Missing a required column in the CSV file: {e}")
        return {}

    print("--- Test data loaded successfully. ---")
    return dict(results)

def getAllSubsystems():
    subsys_list = []
    try:
        with open(SUBSYSTEM_PATH, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                ip = sanitize_filename(row["IP"].strip())
                slt_yn = row["Part of SLT (Y/N)"]
                if slt_yn == 'Y' and ip != 'none' and ip not in subsys_list:
                    subsys_list.append(ip)
                    
    except FileNotFoundError:
        print(f"ERROR: The file was not found at: {SUBSYSTEM_PATH}")
        return {}
    except KeyError as e:
        print(f"ERROR: Missing a required column in the CSV file: {e}")
        return {}
    return subsys_list
            
def main(subsystem_name):
    found_list = getTestCommands(subsystem_name)
    print(found_list)
    for ip in found_list:
        print(f"IP: {ip}")
        for command_info in found_list.get(ip):
            testType = command_info.get("TestType")
            command = command_info.get("Command")
            print(f"    Test Type:{testType}")
            print(f"            Test Command:{command}")
if __name__ == '__main__':
    # main('aoss_aonss')
    # ip = _load_all_test_data()
    # print(ip)
    # print(list(ip.keys()))
    print(getAllSubsystems())