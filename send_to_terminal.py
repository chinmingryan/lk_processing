#!/usr/bin/env python3
import argparse, os, serial, time, logging
from datetime import datetime
from constants import HANG_MARKER

DELAY = 0.2
# Return statements for runCommand()
ERROR_MSG = 2
ERROR = 1
SUCCESS = 0
# Hang patterns
class MultiLineFormatter(logging.Formatter):
    def format(self, record):
        full_msg = super().format(record)
        lines = full_msg.splitlines()
        if len(lines) <= 1:
            return full_msg
        
        prefix = full_msg[:full_msg.find(record.getMessage())]
            # Add prefix to every line
        return "\n".join([lines[0]] + [prefix + line for line in lines[1:]])

class PortRunner():
    def __init__(self, prt, timeout_arg = 100, delay = DELAY, verbosity = False, logName = 'terminal'):
        self.prt = prt
        self.delay = delay
        self.verbosity = verbosity
        self.original_fh_level = None

        # This will now be our single point of connection logic
        self.ser = serial.Serial(
            port=self.prt,
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout= timeout_arg  # In seconds, longest time to run set by
                        # google_tests -n e24_multi_ch_dram_to_dram_dma_test
        )
        self.ser.isOpen()
        print(f'Opened serial port: {self.prt}')
        
        # Initialize logger
        self.logger = logging.getLogger(logName)
        self.logger.setLevel(logging.INFO)
        # Set Console Handler
        has_console = any(type(h) is logging.StreamHandler for h in self.logger.handlers)
        
        if not has_console:
            self.ch = logging.StreamHandler()
            self.ch.setFormatter(logging.Formatter('%(message)s'))
            # Only add it if it didn't exist
            if self.verbosity: self.logger.addHandler(self.ch)
        else:
            # If it exists, grab the existing one in case we need to remove it later
            for h in self.logger.handlers:
                if type(h) is logging.StreamHandler:
                    self.ch = h

    def close(self):
        self.ser.close()
        print(f'Closed port:{self.prt}')
    
    def startLogger(self, log_file_name, name = None):
        # If this logger already has a FileHandler, don't add another one.
        if any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            print(f"Logger '{self.logger.name}' already logging to file. Skipping new handler.")
            return
        
        print(f'Creating logger file at {log_file_name}')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(log_file_name, exist_ok=True)
        if name != None: log_file = os.path.join(log_file_name, f'{name}.log')
        else: log_file = os.path.join(log_file_name, f'{timestamp}.log')
        self.fh = logging.FileHandler(log_file, mode="a")
        formatter = MultiLineFormatter("%(message)s")
        self.fh.setFormatter(formatter)
        self.logger.addHandler(self.fh)
    
    def resumeLogger(self):
        if hasattr(self, 'fh') and self.original_fh_level is not None:
            self.fh.setLevel(self.original_fh_level)
        else:
            print("File logger not paused or active, nothing to resume")
    
    def pauseLogger(self):
        if hasattr(self, 'fh') and self.fh in self.logger.handlers:
            # Store the orignal level so we can restore it later
            self.original_fh_level = self.fh.level
            self.fh.setLevel(logging.CRITICAL + 1)
        else:
            print("File logger not active, nothing to pause.")

    def stopLogger(self):
        # Added a check to prevent errors if handler was already removed
        if hasattr(self, 'fh'):
            self.logger.removeHandler(self.fh)

    def runCommand(self, command, ignore_fail = False, expect_response = 'gsp ]'):
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        if command[:-2] != '\n': self.ser.write(f'{command}\n'.encode())
        elif command[:2] == '\n': self.ser.write(f'{command}'.encode())
        response = self.ser.read_until(expect_response.encode())
        if response[-5:].decode('utf-8', errors='ignore') != expect_response:
            self.ser.write('\n'.encode())
            retry_response = self.ser.read_until(expect_response.encode())
            if retry_response[-5:].decode('utf-8', errors='ignore') != expect_response:
                self.logger.info(f"{response.decode(errors='ignore').strip()}")
                self.logger.info(HANG_MARKER)
                return ERROR
        elif not ignore_fail and ((b'\x1b[31m' in response) or (b'\x1b[91m' in response)):
            self.logger.info(f"{response.decode(errors='ignore').strip()}")
            return ERROR_MSG
        self.logger.info(f"{response.decode(errors='ignore').strip()}") # Store the output
        time.sleep(self.delay)
        return SUCCESS

    
    def setVerbosity(self, flag):
        self.verbosity = flag
        if self.verbosity:
            self.logger.addHandler(self.ch)
        elif not self.verbosity and self.ch in self.logger.handlers:
            self.logger.removeHandler(self.ch)
        else:
            print("Verbosity input was not True/False")
    
    def startFastbootServer(self):
        self.ser.write("google_tests -n fastboot_start -a 2\n")
        time.sleep(3)
        self.ser.write("\n")
        response = self.ser.read_until(b'gsp ]')
        if response[-5:].decode('utf-8', errors='ignore') != "gsp ]":
            self.ser.write('\n'.encode())
            retry_response = self.ser.read_until(b'gsp ]')
            if retry_response[-5:].decode('utf-8', errors='ignore') != "gsp ]":
                return ERROR
        elif b'\x1b[31m' in response or b'\x1b[91m' in response:
            return ERROR_MSG
        self.logger.info(f"{response.decode(errors='ignore').strip()}")
        time.sleep(self.delay)
        return SUCCESS


def testHarness(prt):
    port = PortRunner(prt, verbosity=True)
    port.startLogger('test')
    port.runCommand('cpu_ping')
    port.pauseLogger()
    port.runCommand('cpu_ping')
    port.resumeLogger()
    port.runCommand('cpu_ping')
    port.setVerbosity(False)
    port.runCommand('cpu_ping')
    port.close()
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Send commands from a file to a Minicom pseudo-terminal (PTY)."
    )
    parser.add_argument(
        "-p",
        "--pts_dir", 
        type=str,
        help="Path to the directory containing the Minicom PTY device (e.g., ~/dhub-pts/).",
        default="/usr/local/google/home/chinmingryan/dhub-pts/52131FDSC02348/apc"
    )
    args = parser.parse_args()
    testHarness(args.pts_dir)