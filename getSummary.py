#!/usr/bin/env python3
# Author: Chin Ming Ryan Wong

import os
import re
from collections import defaultdict
from datetime import datetime
import time
import argparse
import logging
from constants import LOG_PARSE_MARKER, TEST_MARKERS, TEST_CONTENT_END_MARKERS, HANG_MARKER, ERROR_MSG_MARKERS, SUCCESS_END_MARKER
from constants import RESULT_PATTERN, RESULT_PATTERN_1, FALSE_TEST_MARKERS
class MultiLineFormatter(logging.Formatter):
    def format(self, record):
        full_msg = super().format(record)
        lines = full_msg.splitlines()
        if len(lines) <= 1:
            return full_msg
        
        prefix = full_msg[:full_msg.find(record.getMessage())]
            # Add prefix to every line
        return "\n".join([lines[0]] + [prefix + line for line in lines[1:]])

def analyzeLog(logPath: str) -> dict:
    """
    Analyzes a log file for test results without creating any new files.

    Args:
        logPath (str): The full path to the log file.

    Returns:
        dict: A dictionary containing detailed analysis results, or None if an error occurs.
    """
    # --- Part 1: Analyze test results from the original log file ---
    
    test_stats = defaultdict(lambda: {
        'total': 0, 'success': 0, 'timeout': False,
        'failures': [], 'ignored': [], 'hangs': [],
        'error_msg': 0
    })
    cmd_hang = {'count':0, 'line': []}
    iteration_num = 0

    try:
        with open(logPath, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Log file not found at '{logPath}'")
        return None

    lines_iterator = iter(enumerate(lines, 1)) # Start enumeration at 1 for line numbers
    line_buffer = None

    while True:
        # Stay on the same line if line_buffer is not empty
        if line_buffer:
            i, line = line_buffer
            line_buffer = None
        else:
        # Manually move onto the next line
            try:
                i, line = next(lines_iterator)
            except StopIteration:
                break   # End of file

        if LOG_PARSE_MARKER in line: iteration_num += 1
        if HANG_MARKER in line:
            cmd_hang['count'] += 1
            cmd_hang['line'].append(i)
        
        # Check if the line contains a start of a test command
        is_test = any(m in line for m in TEST_MARKERS)
        is_invalid = any(m in line for m in ERROR_MSG_MARKERS + FALSE_TEST_MARKERS)
        if is_test and not is_invalid:
            found_indices = (line.find(marker) for marker in TEST_MARKERS if line.find(marker) != -1)
            marker_index = min(found_indices, default=-1)
            test_args = line[marker_index:].strip()
            test_stats[test_args]['total'] += 1

            match = None
            match_1 = None
            # To store hard coded success test commands
            match_success = None
            
            result_line_num = -1

            for j, next_line in lines_iterator:
                is_test_iter = any(m in next_line for m in TEST_MARKERS)
                is_invalid_iter = any(m in next_line for m in ERROR_MSG_MARKERS + FALSE_TEST_MARKERS)
                if LOG_PARSE_MARKER in next_line: iteration_num += 1
                elif is_test_iter and not is_invalid_iter:
                    # Save current line in outer while loop
                    line_buffer = (j, next_line)
                    break
                # Add a hang counter when a hang is detected
                if HANG_MARKER in next_line.strip():
                    test_stats[test_args]['hangs'].append({'count': 1, 'line': j})
                # Increment error message counter if line contains error 
                if any(marker in next_line.strip() for marker in ERROR_MSG_MARKERS):
                    test_stats[test_args]['error_msg'] += 1
                # Hardcoded test command success
                if any(marker in next_line.strip() for marker in SUCCESS_END_MARKER):
                    match_success = True
                    break
                # Found test results, store result num in match or match_1
                # Otherwise, both match is 'None'
                if "Total Execution Time:" in next_line.strip():
                    for k, content_end_line in lines_iterator:
                        if any(marker == content_end_line.strip() for marker in TEST_CONTENT_END_MARKERS):
                            for l, result_line in lines_iterator:
                                match = RESULT_PATTERN.search(result_line)                                  
                                match_1 = RESULT_PATTERN_1.search(result_line)
                                if match or match_1:
                                    result_line_num = l # This is the original line number
                                    break 
                                if l >= j + 3: # Stop searching after 3 lines
                                    break
                            break
                        if k >= j + 3:
                            print("No elapsed timer found")
                            break
            if match:
                tests, failures, ignored = map(int, match.groups())
                if failures > 0:
                    test_stats[test_args]['failures'].append({'count': 1, 'line': result_line_num})
                if ignored > 0:
                    test_stats[test_args]['ignored'].append({'count': 1, 'line': result_line_num})
                if failures == 0 and ignored == 0:
                    test_stats[test_args]['success'] += 1
            elif match_1:
                print("hsio_ufs test detected")
                tests = int(match_1.groups()[0])
                l, next_line = next(lines_iterator)
                # Find failure
                match_1 = RESULT_PATTERN_1.search(next_line)
                failures = int(match_1.groups()[0])
                if failures > 0:
                    test_stats[test_args]['failures'].append({'count': 1, 'line': result_line_num})
                if failures == 0:
                    test_stats[test_args]['success'] += 1
            elif match_success:
                print(f"Hardcoded success detected for test '{test_args}' starting at line {i}")
                test_stats[test_args]['success'] += 1
            else:
                print(f"Timeout or no result found for test '{test_args}' starting at line {i}")
                test_stats[test_args]['timeout'] = True
                test_stats[test_args]['hangs'].append({'count': 1, 'line': j-1})

    # --- Part 2: Aggregate data ---
    total_runs = sum(stats['total'] for stats in test_stats.values())
    total_passed = sum(stats['success'] for stats in test_stats.values())
    total_failures = sum(sum(f['count'] for f in stats['failures']) for stats in test_stats.values())
    total_hangs = sum(sum(h['count'] for h in stats['hangs']) for stats in test_stats.values())
    total_ignored = sum(sum(i['count'] for i in stats['ignored']) for stats in test_stats.values())
    timeout_detected = any(stats['timeout'] for stats in test_stats.values())
    total_error_msg = sum(stats['error_msg'] for stats in test_stats.values())

    results = {
        "iterations": iteration_num,
        "total_tests": total_runs,
        "total_passed": total_passed,
        "total_failed": total_failures,
        "total_hangs": total_hangs,
        "total_ignored": total_ignored,
        "timeout_flag": timeout_detected,
        "test_stats": test_stats,
        "total_error_msg": total_error_msg,
        "cmd_hang": cmd_hang
    }
    return results

def log_test_summary(results_dict: dict, log_path: str):
    """
    Creates and saves a formatted summary from a test results dictionary to a log file.

    Args:
        results_dict (dict): The dictionary returned by analyzeLog.
        log_path (str): The path to the file where the summary should be saved.
    """
    # Use a unique logger name to avoid conflicts
    logger = logging.getLogger('summary_logger')
    logger.setLevel(logging.INFO)
    
    # Ensure the directory for the log file exists
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    # Create a file handler that appends to the specified log file
    fh = logging.FileHandler(log_path, mode="a")
    fh.setFormatter(MultiLineFormatter("%(message)s"))
    logger.addHandler(fh)

    if not results_dict:
        logger.error("Analysis could not be completed.")
        logger.removeHandler(fh) # Clean up handler
        return
    
    logger.info('----------------------- Test Summary -----------------------')
    logger.info(f'Total iterations: {results_dict["iterations"]}')
    logger.info(f"{results_dict['total_tests']} Tests {results_dict['total_failed']} Fails {results_dict['total_ignored']} Ignored {results_dict['total_hangs']} Hangs {results_dict['total_error_msg']} Error Messages")
    if results_dict["timeout_flag"]:
        logger.warning("\nWARNING: One or more tests may have timed out (result summary not found).")

    if not results_dict['total_failed'] and not results_dict['total_ignored'] and not results_dict['total_hangs']:
        logger.info("\nPASSED")
    else:
        logger.info("\n--- Failed tests ---")
        failed_tests_found = False
        for test, stats in results_dict['test_stats'].items():
            for fail_info in stats['failures']:
                logger.info(
                    f"'{test}': {fail_info['count']} failure(s) found on line {fail_info['line']}"
                )
                failed_tests_found = True
        if not failed_tests_found:
            logger.info("None")
        
        logger.info("\n--- Ignored tests ---")
        ignored_tests_found = False
        for test, stats in results_dict['test_stats'].items():
            for ignore_info in stats['ignored']:
                logger.info(
                    f"'{test}': {ignore_info['count']} ignored found on line {ignore_info['line']}"
                )
                ignored_tests_found = True
        if not ignored_tests_found:
            logger.info("None")
        
        logger.info("\n--- Hanged tests ---")
        hang_tests_found = False
        for test, stats in results_dict['test_stats'].items():
            for hang_info in stats['hangs']:
                logger.info(
                    f"'{test}': {hang_info['count']} hangs found on line {hang_info['line']}"
                )
                hang_tests_found = True
        if not hang_tests_found:
            logger.info("None")
        logger.info("\n--- Hanged commands ---")
        if results_dict.get("cmd_hang").get("count") != 0:
            for hang_line in results_dict.get("cmd_hang").get("line"):
                logger.info(f"1 hang found on line {hang_line}")
        else:
            logger.info("None")

    # Clean up by removing the handler so the file is closed and logger is freed
    logger.removeHandler(fh)
    
def main(log_file: str):
    # Create a summary log file from original log
    analysis = analyzeLog(log_file)
    dir, base = os.path.split(log_file)
    base, ext = os.path.splitext(base)
    summary_path = os.path.join(dir, f"{base}_summary.log")
    log_test_summary(analysis, summary_path)

# --- Example Usage ---
if __name__ == '__main__':
    ip = 'cpu_ccm2'
    parser = argparse.ArgumentParser(description="Compare FIH and BenchVal logs against a test plan and analyze failures.")
    parser.add_argument('-l', '--log', type=str, required=False, help="Path to the log .txt file.",
                        # default=f'/usr/local/google/home/chinmingryan/Documents/logs/mbu/{ip}.log')
                        default=f'/usr/local/google/home/chinmingryan/Documents/logs/mbu/test_command_output/mbu_b0_v5p2_ebu_883217b6e6e5ed766c652e82e8f24325.log')
    args = parser.parse_args()
    start_time = time.perf_counter()

    # Create a summary log file from original log
    main(args.log)

    # Print out elapsed time
    end_time = time.perf_counter()
    elapsed_ms = int((end_time - start_time) * 1000)
    print(f"Total Execution Time: {elapsed_ms} (ms)")