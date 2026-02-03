#!/usr/bin/env python3
# Author: Chin Ming Ryan Wong

import argparse, os, serial, time, logging, csv, subprocess, threading, shutil
from send_to_terminal import PortRunner, ERROR_MSG, ERROR
from dhub_automation import DhubAutomation
import serial_num_util, getSummary
from constants import LOG_OUTPUT_DIR

class MultiLineFormatter(logging.Formatter):
    def format(self, record):
        full_msg = super().format(record)
        lines = full_msg.splitlines()
        if len(lines) <= 1:
            return full_msg
        
        prefix = full_msg[:full_msg.find(record.getMessage())]
            # Add prefix to every line
        return "\n".join([lines[0]] + [prefix + line for line in lines[1:]])

def run_SOP(test_plan, soc_sn, brd_sn, package_path, iteration, timoeut =  120):
    # Fail flag for skipping to next <reboot>
    crit_err = False
    # Start dhub
    dhub_inst = DhubAutomation(soc_sn)
    # Get APC port
    try:
        soc_ports = dhub_inst.get_dhub_ports()
        apc_port = soc_ports["APC"]
        aoss_port = soc_ports["AOSS_SENSOR_CORE"]
        aoss_a32_port = soc_ports["AOSS_A32"]
    except KeyError as e:
        dhub_inst.stop_dhub()
        print(f"Error retrieving APC port: {e}")
    # Start APC terminal
    # Timeout set by longest test in MBU set by
    #   google_tests -v -n concurrency_fabdisp_stress -a g2d dpu cpu_memcpy cpu_memcpy cpu_memcpy cpu_memcpy dvfs_fabdisp
    port = PortRunner(apc_port, verbosity=False, timeout_arg = timoeut, logName= soc_sn)
    for i in range(int(iteration)):
        try:
            # Open the serial port
            with open(test_plan) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    command = row["Command"].strip()
                    if "AOSS_SENSOR_CORE: " in command and not crit_err:
                        # print(f'Sending AOSS command: {command.replace("AOSS_SENSOR_CORE: ","")}')
                        # Add AOSS command logging here
                        port_aoss = PortRunner(aoss_port, verbosity=False, timeout_arg = timoeut, logName= soc_sn)
                        port_aoss.ser.write(f'{command.replace("AOSS_SENSOR_CORE: ","")}\n'.encode())
                        full_response = b""
                        for _ in range(2):
                            chunk = port_aoss.ser.read_until(b'e24]')
                            full_response += chunk
                        decoded_response = full_response.decode('utf-8', errors='ignore')
                        port_aoss.logger.info(f"{decoded_response}")
                        # port_aoss.runCommand(command.replace("AOSS_SENSOR_CORE: ",""), expect_response="e24]",)
                    elif "AOSS_A32 uart: " in command and not crit_err:
                        # print(f'Sending AOSS A32 command: {command.replace("AOSS_A32 uart: ","")}')
                        # Add AOSS A32 command logging here
                        port_aoss_a32 = PortRunner(aoss_a32_port, verbosity=False, timeout_arg = timoeut, logName= soc_sn)
                        port_aoss_a32.ser.write(f'{command.replace("AOSS_A32 uart: ","")}\n'.encode())
                        full_response = b""
                        for _ in range(2):
                            chunk = port_aoss_a32.ser.read_until(b'a32]')
                            full_response += chunk
                        decoded_response = full_response.decode('utf-8', errors='ignore')
                        port_aoss_a32.logger.info(f"{decoded_response}")
                        # port_aoss_a32.runCommand(command.replace("AOSS_A32: ",""), expect_response="a32]",)

                    elif '<' not in command and '>' not in command and not crit_err:
                        # print(f'Sending test: {command}')
                        # Send a command
                        try:
                            port.runCommand(command)
                        except Exception as e:
                            # print(f"Error sending command '{command}': {e}")
                            port.logger.info("-------------Skipping to next reboot-------------")
                            crit_err = True
                    elif '<' in command or '>' in command:
                        cmd_line = command[1:-1].strip()  # Remove the angle brackets
                        if cmd_line == "reboot device":
                            # Stop Port Runner
                            port.stopLogger()
                            port.close()
                            # Stop dhub
                            dhub_inst.stop_dhub()
                            # reboot SoC
                            serial_num_util.creset_and_lk(package_path, soc_sn, brd_sn)
                            # Start dhub again to refresh the connection
                            dhub_inst.__init__(soc_sn)
                            soc_ports = dhub_inst.get_dhub_ports()
                            apc_port = soc_ports["APC"]
                            aoss_port = soc_ports["AOSS_SENSOR_CORE"]
                            port = PortRunner(apc_port, verbosity=False, timeout_arg = timoeut, logName= soc_sn)
                            time.sleep(3)
                            log_name = os.path.basename(test_plan).replace('.csv','')
                            log_name = f"{log_name}_{soc_sn}"
                            # print(f"Starting new log: {log_name}")
                            port.startLogger(LOG_OUTPUT_DIR, name = log_name)
                            # Turn off crit_err flag to skip to next set of test
                            crit_err = False
                
                        # Only load ramdisk if no critical error
                        elif cmd_line.startswith("fastboot") and not crit_err:
                            cmd_line = cmd_line.split()
                            # If the command involves a ramdisk file, prepend the package path
                            if '.ext2' in cmd_line[-1]:
                                ramdisk_path = os.path.join(package_path, cmd_line[-1])
                                cmd_line[-1] = ramdisk_path
                            cmd_line.insert(1, "-s")
                            cmd_line.insert(2, soc_sn)
                            # print(f"Executing fastboot command: {cmd_line}")
                            # Execute the fastboot command
                            fastboot_output = subprocess.run(cmd_line, stdout=subprocess.DEVNULL)
                            if fastboot_output.returncode != 0:
                                port.logger.info("Fastboot command failed. Skipping to next reboot.")
                                crit_err = True
            # Change ownership of log files to user
            port.stopLogger()
            port.close()
            try:
                port_aoss.close()
            except:
                pass

        except serial.SerialException as e:
            print(f"Serial port error: {e}")
            port.close()
            subprocess.run(['sudo', 'chown', '-R', 'chinmingryan', LOG_OUTPUT_DIR])
    # Add summary log generation
    log_dir_path = os.path.join(LOG_OUTPUT_DIR, log_name)
    os.makedirs(log_dir_path,exist_ok=True)
    shutil.move(os.path.join(LOG_OUTPUT_DIR,f"{log_name}.log"), log_dir_path)
    getSummary.main(os.path.join(log_dir_path, f"{log_name}.log"))
    subprocess.run(['sudo', 'chown', '-R', 'chinmingryan', LOG_OUTPUT_DIR])

def device_task(test_plan, soc_sn, brd_sn, lk_package_path, iteration):
    """
    Wrapper function to handle both setup and execution in the thread.
    """
    print(f"[{soc_sn}] Starting setup (Reset & LK)...")
    
    # 1. Move setup INSIDE the thread so it runs in parallel
    serial_num_util.creset_and_lk(lk_package_path, soc_sn, brd_sn)
    
    print(f"[{soc_sn}] Setup complete. Starting SOP execution...")
    
    # 2. Run the actual SOP
    run_SOP(test_plan, soc_sn, brd_sn, lk_package_path, iteration)
    print(f"[{soc_sn}] Task finished.")

def main():
    parser = argparse.ArgumentParser(
        description="Send commands from a file to a Minicom pseudo-terminal (PTY)."
    )
    parser.add_argument(
        "-t",
        "--test_plan", 
        type=str,
        help="Path to the test plan .csv file.",
        default="/usr/local/google/home/chinmingryan/Documents/mbu_lk_related/test_plans/B0/mbu_b0_ebu_cpu_c2.csv"
    )
    parser.add_argument(
        "-k",
        "--lk_package_path",
        type=str,
        help="Path to the directory containing the LK package.",
        default="/usr/local/google/home/chinmingryan/Documents/mbu_lk_related/flash_packs/mbu_b0_v5p2_ebu"
    )
    parser.add_argument(
        "-i",
        "--iteration", 
        type=str,
        help="Number of times to run SOP.",
        default="10"
    )
    args = parser.parse_args()
    if serial_num_util.retrieve_sn_list_from_file() == []:
        print("Serial number pair file not found. Generating new serial number pairs...")
        paired_sn_list = serial_num_util.get_paired_sn()
        serial_num_util.store_sn_list_to_file(paired_sn_list)
    else:
        print("Retrieving serial number pairs from file...")
        paired_sn_list = serial_num_util.retrieve_sn_list_from_file()
    
    threads = []

    print(f"Starting tests for {len(paired_sn_list)} devices...")

    for serial_pair in paired_sn_list:
        soc = serial_pair['soc_sn']
        brd = serial_pair['brd_sn']

        # Create the thread targeting the WRAPPER function
        t = threading.Thread(
            target=device_task, 
            args=(args.test_plan, soc, brd, args.lk_package_path, args.iteration)
        )
        
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    print("All devices have finished execution.")

if __name__ == "__main__":
    main()