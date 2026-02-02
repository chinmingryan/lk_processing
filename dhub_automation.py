import subprocess, os, signal, threading, time
from constants import DHUB_PATH

class DhubAutomation():
    def __init__(self, serial):
        self.dhub_output = None
        self.ports = {}
        # Start dhub in a separate thread to avoid blocking
        threading.Thread(target=self.run_dhub, args=(serial,)).start()
        self.ports_ready = threading.Event()

    def get_dhub_ports(self):
        if not self.ports_ready.wait(timeout=5):
            print("Timeout waiting for dhub ports.")
            return
        else:
            print("Establishing dhub ports...")
            for line in self.dhub_output.stdout:
                if "APC terminal:" in line.decode().strip():
                    apc_term = line.decode().strip().split("APC terminal: ")[-1]
                    self.ports["APC"] = apc_term
                elif "CPM terminal:" in line.decode().strip():
                    cpm_term = line.decode().strip().split("CPM terminal: ")[-1]
                    self.ports["CPM"] = cpm_term
                elif "AOSS_SENSOR_CORE terminal:" in line.decode().strip():
                    aoss_term = line.decode().strip().split("AOSS_SENSOR_CORE terminal: ")[-1]
                    self.ports["AOSS_SENSOR_CORE"] = aoss_term
                elif "AOSS_A32 terminal:" in line.decode().strip():
                    aoss_a32_term = line.decode().strip().split("AOSS_A32 terminal: ")[-1]
                    self.ports["AOSS_A32"] = aoss_a32_term
                # Exit for loop if both ports are found
                if "Launched DHUB. Press Ctrl-C to exit." in line.decode().strip():
                    break
            # Return the ports dictionary
            return self.ports

    def run_dhub(self, serial_num):
        symlink_dir = "./MLB_1"
        if os.path.exists(symlink_dir):
            # Using shell command to be extra thorough with symlinks
            subprocess.run(["rm", "-rf", symlink_dir])
        print("Starting dhub...")
        self.dhub_output = subprocess.Popen(["python3", DHUB_PATH, "--usb", "--usb-endpoint-address", "1"
                                        ,"--usb-vendor-id", "0x18d1", "--usb-product-id", "0x4eef"
                                        ,"--usb-interface-name", "UART and Debug Interface", "-r" 
                                        ,"r3p0", "--usb-serial-number", serial_num
                                        ,"--no-tmux-session", "--pts-symlink-basedir", f"./{serial_num}"
                                        ,"--debug_port_socket_path", f"./{serial_num}/dhub_debug_1_port.sock"]
                                        , stdout=subprocess.PIPE, stderr=subprocess.PIPE
                                        , start_new_session=True)
        self.ports_ready.set()
        
    def stop_dhub(self):
        if self.dhub_output is not None and self.dhub_output.poll() is None:
            print("Terminating dhub process...")
            pgid = os.getpgid(self.dhub_output.pid)
            try:
                # Equivalent to Ctrl+C
                os.killpg(pgid, signal.SIGINT)
            except OSError as e:
                print(f"Error terminating dhub process: {e}")
            
            try:
                # Wait for the process to actually shut down
                self.dhub_output.wait(timeout=10)
                print("dhub process successfully terminated.")
            except subprocess.TimeoutExpired:
                print("dhub process did not terminate gracefully after SIGINT. Forcing SIGKILL.")
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except OSError as e:
                    print(f"Error sending SIGKILL: {e}")
                self.dhub_output.wait()
                print("dhub process forcibly killed.")
        else:
            print("dhub process is not running.")

if __name__ == "__main__":
    serial_num = subprocess.run(["fastboot","devices"], capture_output=True, text=True).stdout.split()[0]
    print(f"Using serial number: {serial_num}")
    # Start dhub thread
    dhub_automation = DhubAutomation(serial_num)
    print(dhub_automation.get_dhub_ports())
    time.sleep(10)  # Let dhub run for a bit
    dhub_automation.stop_dhub()