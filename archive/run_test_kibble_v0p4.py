#!/usr/bin/env python3
# Author: Chin Ming Ryan Wong
# V0.4
import argparse
import subprocess
import shutil
import os
import time
from collections import defaultdict
from zipfile import ZipFile
from archive.get_test_commands import getTestCommands, getAllSubsystems
from send_to_terminal import PortRunner, SUCCESS, ERROR_MSG, ERROR
from ramdisk_lib import mount_ramdisk, find_ramdisk
import getSummary
from constants import TIMEOUT_RUN_IP, FTDI_PATH, STAGE_LK_PATH
from constants import RAMDISK_DIR, LOG_OUTPUT_DIR
from constants import CSV_OUTPUT_PATH, BITS_PATH, BITS_SERVICE_PATH, BITS_EXT

# SoC reboot sequence
def creset_and_lk():
    failCount = 0
    reboot = False
    
    while failCount < 5 and not reboot:
        print(f"Attempting ROM Recovery")
        subprocess.run(['sudo', FTDI_PATH, '5'], stdout=subprocess.DEVNULL)
        print(f"Re-staging for lk")
        output = subprocess.run([STAGE_LK_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if output.returncode != 0: failCount += 1
        else:
            print("LK loaded")
            reboot = True
    # Open fastboot server for ramdisk mounting
    time.sleep(3)

    fb_port = PortRunner(args.pts_dir, verbosity=False, timeout_arg = 0, logName='fb_temp_logger')
    print(f"Opening fastboot server")
    fb_port.runCommand("google_tests -n fastboot_start -a 2")
    fb_port.close()

    time.sleep(2)


# Kibble Functions
def start_bits_service():
    bs_process = subprocess.Popen(BITS_SERVICE_PATH, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if bs_process.returncode != 0:
        raise RuntimeError(f"Background process: {bs_process.args} Returned with code {bs_process.returncode}")

def start_collection(title):
    # print(f'Starting kibble recording for {title}')
    subprocess.run([BITS_PATH,"--duration", "180s", "--create", title])
    time.sleep(0.1)

def stop_collection(title):
    subprocess.run([BITS_PATH,'--stop', title])

def export_collection(title, title_path):
    print(f'Exporting {title} as .7z.bits to {title_path}')
    subprocess.run([BITS_PATH, "--export", title, "--export_file", title_path])

def delete_collection(title):
    subprocess.run([BITS_PATH, '--delete', title])

def clear_collection():
    subprocess.run([BITS_PATH, '--clear'])

def unique_filename(directory: str, filename: str) -> str:
    """
    Ensures the filename is unique inside the given directory.
    If 'filename.ext' exists, returns 'filename_1.ext', 'filename_2.ext', etc.
    """

    if filename.endswith(BITS_EXT):
        base = filename.removesuffix(BITS_EXT)
        ext = BITS_EXT
    else:
        # Fallback to the standard split if it's not a .7z.bits file
        base, ext = os.path.splitext(filename)

    candidate = filename
    counter = 1
    
    while os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    
    return candidate

# Main function
def run_ip(ip_name , pts_dir, log_dir, run_kibble = False):
    fail_flag = False
    test_list_data = getTestCommands(ip_name)
    error_ip = defaultdict(lambda: defaultdict(int))
    test_cmd_list_for_zip = []      # Tracks kibble record for zip file


    if ip_name not in test_list_data:
        print(f"No tests found for IP: {ip_name}")
        return {}

    # This is now a list of commands in the correct order
    command_sequence = test_list_data[ip_name]

    print(f'--- Starting IP: {ip_name} ---')
    if 'hsio_pcie' in ip_name or 'lsio_gpio' in ip_name:
        test_timeout = 10
    else:
        test_timeout = TIMEOUT_RUN_IP
    port = PortRunner(pts_dir, timeout_arg = test_timeout, verbosity=False)
    port.startLogger(log_dir, name=ip_name)
    port.runCommand('otp_tool get_serial_num')

    for command_info in command_sequence:
        test_type = command_info["TestType"]
        test_command = command_info["Command"]
        # Kibble zip file list
        print(f"\nProcessing command (Type: {test_type}): {test_command}")

        if test_type == "command":
            response = port.runCommand(test_command)
            if response == ERROR:
                port.logger.info(f"")
                print(" Command hanged SoC")
                port.stopLogger()
                creset_and_lk()
                if find_ramdisk(ip_name) != 0:
                    if mount_ramdisk(find_ramdisk(ip_name), RAMDISK_DIR) == 1:
                        creset_and_lk()
                        mount_ramdisk(find_ramdisk(ip_name), RAMDISK_DIR)
                port.__init__(pts_dir, timeout_arg = test_timeout, verbosity=False)
                print("     PortRunner re-initialized successfully.")
                port.startLogger(log_dir, name=ip_name) # Restart logger after re-init

        elif test_type == "test":
            if run_kibble:
                ip_dir_path = os.path.join(CSV_OUTPUT_PATH, ip_name)
                os.makedirs(ip_dir_path, exist_ok=True)
                # Create a unique filename for the kibble data
                sanitized_cmd = test_command.replace('.', '_').replace(' ', '_')
                title_candidate = unique_filename(ip_dir_path, f'{sanitized_cmd}.7z.bits')
                title = title_candidate[:-8]
                title_path = os.path.join(ip_dir_path, title_candidate)
                
            error_ip[ip_name]['test'] += 1
            
            try:
                # Start kibble collection
                if run_kibble: start_collection(title)
                print(f"    Running")
                # Run command
                response = port.runCommand(test_command)
                if response == ERROR:
                    raise ValueError('      Test command hanged SoC')
                elif response == ERROR_MSG and not fail_flag:
                    print("         Error message detected")
                    error_ip[ip_name]['error_msg'] += 1
            except Exception as e:
                print(e)
                if run_kibble:
                    # Stop bad kibble collection
                    stop_collection(title)
                    # Delete bad kibble collection
                    delete_collection(title)
                port.stopLogger()
                creset_and_lk()
                if find_ramdisk(ip_name) != 0:
                    if mount_ramdisk(find_ramdisk(ip_name), RAMDISK_DIR) == 1:
                        creset_and_lk()
                        mount_ramdisk(find_ramdisk(ip_name), RAMDISK_DIR)
                port.__init__(pts_dir, timeout_arg = test_timeout, verbosity=False)
                print("     PortRunner re-initialized successfully.")
                port.startLogger(log_dir, name=ip_name) # Restart logger after re-init
                error_ip[ip_name]['hangs'] += 1
                # After a fatal error, we skip export kibble data
                continue

            # Stop and export kibble collection
            if run_kibble:
                try:
                    stop_collection(title)
                    export_collection(title, title_path)
                    test_cmd_list_for_zip.append(title_path)
                except Exception as e:
                    print(f"Error during kibble export: {e}")
                    fail_flag = True
                    stop_collection(title)
                    delete_collection(title)

        elif test_type == "fastboot":
            # Extract ramdisk file from the command string
            try:
                ramdisk_path = test_command.split()[-1]
                ramdisk_file = os.path.basename(ramdisk_path)
                print(f"Mounting ramdisk: {ramdisk_file}")
                port.stopLogger()
                if mount_ramdisk(find_ramdisk(ip_name), RAMDISK_DIR) == 1:
                        creset_and_lk()
                        mount_ramdisk(find_ramdisk(ip_name), RAMDISK_DIR)
                port.__init__(pts_dir, timeout_arg = test_timeout, verbosity=False) # Re-initialize the port object
                port.startLogger(log_dir, name=ip_name) # Restart the logger
            except IndexError:
                print(f"ERROR: Could not parse ramdisk file from command: '{test_command}'")


        elif test_type == "reboot":
            print("--- Executing reboot ---")
            port.stopLogger()
            creset_and_lk()
            port.__init__(pts_dir, timeout_arg = test_timeout, verbosity=False) # Re-initialize the port object
            port.startLogger(log_dir, name=ip_name) # Restart the logger            

    port.stopLogger()
    port.close()

    # Generate summary log
    # Define the original log file path (e.g., .../test_command_output/aoss_ambss.log)
    original_log_path = os.path.join(log_dir, f'{ip_name}.log')
    
    if os.path.exists(original_log_path):
        # 1. Create a new directory named after the IP
        #    (e.g., .../test_command_output/aoss_ambss/)
        ip_log_dir = os.path.join(log_dir, ip_name)
        os.makedirs(ip_log_dir, exist_ok=True)

        # 2. Define the new, final path for the log file
        log_filename = os.path.basename(original_log_path)
        new_log_path = os.path.join(ip_log_dir, log_filename)

        # 3. Move the log file into its new directory
        try:
            shutil.move(original_log_path, new_log_path)
        except Exception as e:
            print(f"Warning: Could not move log file {original_log_path}. It may be in use. Error: {e}")
            # Try to continue if the file is already there
            if not os.path.exists(new_log_path):
                 print(f"CRITICAL: Log file not found at {new_log_path}. Aborting summary.")

        # 4. Run analysis on the log file in its new location
        results = getSummary.analyzeLog(new_log_path)
        
        # 5. Define the summary path, also inside the new directory
        summary_log_path = os.path.join(ip_log_dir, f'{ip_name}_summary.log')

        # 6. Save the summary log in the new directory
        getSummary.log_test_summary(results, summary_log_path)

    # Zip kibble collections
    if run_kibble:
    # --- Zipping and Cleanup (runs once per IP) ---
        ip_dir_path = os.path.join(CSV_OUTPUT_PATH, ip_name)
        if not fail_flag and test_cmd_list_for_zip:
            zip_path = f'{ip_dir_path}.zip'
            print(f"\nZipping results for {ip_name} to {zip_path}")
            with ZipFile(zip_path, 'w') as zipf:
                for full_file_path in test_cmd_list_for_zip:
                    file_name = os.path.basename(full_file_path)
                    print(f"Zipping: {file_name}")
                    zipf.write(full_file_path, arcname=file_name)
            
            # Clean up the directory after zipping
            shutil.rmtree(ip_dir_path)
            # Delete all collections from Bits Client
            subprocess.run(['sudo', 'chown', '-R', 'chinmingryan', CSV_OUTPUT_PATH])
        clear_collection()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Send commands from a file to a Minicom pseudo-terminal (PTY)."
    )
    parser.add_argument(
        "-t",
        "--test_subsys", 
        type=str,
        help="Name of Subsystem to run tests on (e.g. ['ams', 'cpu_general', 'gpu' ...] or tpu or all to run all subsystems)",
        nargs='*',  # Expect 0 or more arguments seperated by spaces and turns them into a list
        default = ['gpca']
    )
    parser.add_argument(
        "-p",
        "--pts_dir", 
        type=str,
        help="Path to the directory containing the Minicom PTY device (e.g., ~/dhub-pts/).",
        default="/usr/local/google/home/chinmingryan/dhub-pts/52131FDSC02348/apc"
    )
    parser.add_argument(
        "-i",
        "--rerun_num", 
        type=int,
        help="Number of times to rerun Subsystem.",
        default="1"
    )
    parser.add_argument(
        "-k",
        "--run_kibble", 
        type=str,
        help="Run kibble y/n.",
        default="n"
    )
    args = parser.parse_args()

    start_time = time.perf_counter()

    if args.run_kibble == 'n': kibble_bool = False
    else: kibble_bool = True

    creset_and_lk()
    for i in range(args.rerun_num):

        if args.rerun_num > 1: log_path = os.path.join(LOG_OUTPUT_DIR, str(i))
        else: log_path = LOG_OUTPUT_DIR     # Don't make a directory if only 1 iteration
        print(args.test_subsys)
        if args.test_subsys[0] == "all":
            all_subsys = getAllSubsystems()
            for ip in all_subsys:
                ip_errors = run_ip(ip, args.pts_dir, log_path, kibble_bool)
        elif isinstance(args.test_subsys, list):
            for ip in args.test_subsys:
                ip_errors = run_ip(ip, args.pts_dir, log_path, kibble_bool)
        elif isinstance(args.test_subsys, str):
            ip_errors = run_ip(args.test_subsys, args.pts_dir, log_path, kibble_bool)
        else:
            ip_errors = 0
            print("No list provided")
    
    # Re-assign all logs to user ownership
    subprocess.run(['sudo', 'chown', '-R', 'chinmingryan', LOG_OUTPUT_DIR])

    end_time = time.perf_counter()
    elapsed_ms = int((end_time - start_time) * 1000)
    print(f"Total Execution Time: {elapsed_ms} (ms)")