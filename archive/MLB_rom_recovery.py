#!/usr/bin/env python3
# Author: Chin Ming Ryan Wong

import subprocess
import time
import sys

def run_command_until_success(command):
    """
    Runs a given command repeatedly until it succeeds
    (returns a 0 exit code).

    Args:
        command (list): The command to run as a list of strings.

    Returns:
        bool: True if the command succeeded, False if a fatal error occurred.
    """
    command_str = ' '.join(command)
    print(f"Attempting to run: '{command_str}'")
    print("Will retry every 1 second until the command succeeds...")
    print("-" * 30)

    while True:
        try:
            # Run the command
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)

            # Check if the command was successful
            if result.returncode == 0:
                print(f"\nCommand Succeeded: '{command_str}'")
                if result.stdout:
                    print(f"Output (stdout):\n{result.stdout.strip()}")
                print("-" * 30)
                return True  # Signal success
            else:
                # Command failed, print the error from stderr
                error_output = result.stderr.strip()
                if not error_output and result.stdout.strip():
                    error_output = result.stdout.strip()  # Sometimes errors are on stdout
                
                print(f"Command failed: {error_output}. Retrying in 1s...")

        except FileNotFoundError:
            print(f"FATAL ERROR: '{command[0]}' command not found.")
            print(f"Please ensure '{command[0]}' is installed and in your system's PATH.")
            return False  # Signal fatal error
            
        except subprocess.TimeoutExpired:
            print("Command timed out. Retrying in 1s...")
            
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Retrying in 1s...")

        # Wait for 1 second before trying again
        time.sleep(1)

def run_reboot_sequence():
    """
    Runs the full reboot sequence:
    1. 'adb reboot bootloader' until success
    2. 'fastboot oem reboot-rom' until success
    Then prints the total time taken.
    """
    
    # Define the commands
    adb_command = ["adb", "reboot", "bootloader"]
    fastboot_command = ["fastboot", "oem", "reboot-rom"]
    
    # Record the start time using a monotonic clock
    start_time = time.monotonic()
    
    # Run the first command
    if not run_command_until_success(adb_command):
        print("Exiting due to fatal error with adb command.")
        sys.exit(1)
        
    # Run the second command
    if not run_command_until_success(fastboot_command):
        print("Exiting due to fatal error with fastboot command.")
        sys.exit(1)

    # Calculate and print the total time
    end_time = time.monotonic()
    total_time = end_time - start_time
    
    print("Both commands succeeded!")
    print(f"Total time for sequence: {total_time:.2f} seconds.")

if __name__ == "__main__":
    run_reboot_sequence()


