from datetime import datetime
from re import compile

# serial_num_util.py constants
# Subsystem Test execution paths
FTDI_MULTI_PATH = "./ftdi_multi_sn.sh"
STAGE_LK_PATH = "./stage_for_lk_multi_sn.sh"

# send_to_terminal_batch_v2.py constants
# Log path
LOG_OUTPUT_DIR = "/usr/local/google/home/chinmingryan/Documents/logs/mbu/test_command_output"

# getSummary.py constants
# Marker to identify the start of a new iteration to split.
LOG_PARSE_MARKER = "otp_tool get_serial_num"
# Marker to identify a test run.
TEST_MARKERS = ["google_tests ", "jedec_ufs ", "aon ", "gsa "]
FALSE_TEST_MARKERS = ['"google_tests', 'cpm-exec', 'aon =', 'I gsa.test:']
# Return line
RETURN_LINE = "gsp ]"
# Test content  markers
HANG_MARKER = "--------Hang--------"
ERROR_MSG_MARKERS = ['\x1b[31m', '\x1b[91m']        # ANSII Color Codes for errors
GPCA_END_MARKER = "gsa: "
TEST_CONTENT_END_MARKERS = ["-----------------------", "*********** TEST SUMMARY **************"]
AOSS_AON_SCR_END_MARKER = "I aon_toolbox: E20 firmware already running"
SUCCESS_END_MARKER = ["gsa: Test Passed", "returned 0 --> PASS"]
RESULT_PATTERN = compile(r"(\d+)\s+Tests\s+(\d+)\s+Failures\s+(\d+)\s+Ignored")
RESULT_PATTERN_1 = compile(r"(?:PASSED|FAILED) - (\d+)") # hsio_ufs test result pattern

# dhub_automation.py constants
DHUB_PATH = "./dhub.pyz"

# blink_test.py constants
SN_PAIR_FILE = "/usr/local/google/home/chinmingryan/Documents/mbu_lk_related/paired_serial_numbers.txt"

#run_test_kibble constants
TIMEOUT_RUN_IP = 100
BITS_EXT = '.7z.bits'

RAMDISK_DIR = "/usr/local/google/home/chinmingryan/Documents/mbu_lk_related/flash_packs/mbu_a0_slt_proto1p0_ep/prebuilts/mbu"

# Kibble paths
CSV_OUTPUT_PATH = f'/usr/local/google/home/chinmingryan/Documents/kibble_data/{datetime.now().strftime("%Y%m%d")}'
BITS_PATH = "/usr/local/google/home/chinmingryan/bits/bits"
BITS_SERVICE_PATH = "/usr/local/google/home/chinmingryan/bits/bits_service"

# get_test_commands.py constants
SUBSYSTEM_PATH = "/usr/local/google/home/chinmingryan/Documents/mbu_lk_related/test_plans/SoC Bench Validation Report_MBU_A0.csv"
_CACHED_TEST_DATA = None

# log2csv.py constants
FIELDNAMES = ["Subsystem", "Total Tests", "Pass", "Fail", "Hang"]
SUMMARY_PATTERN = compile(r"(\d+)\s+Tests\s+(\d+)\s+Fails\s+(\d+)\s+Ignored\s+(\d+)\s+Hangs\s+(\d+)\s+Error\s+Messages")