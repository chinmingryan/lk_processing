import argparse
import os, re, csv, glob
from archive.get_test_commands import getAllSubsystems
from constants import FIELDNAMES, SUMMARY_PATTERN
class CSVSummary:
    def __init__(self, csv_out_dir):
        self.file_name = f"{csv_out_dir}.csv"
        self.file_exists = os.path.isfile(self.file_name)
        self.summary_log_paths = []
        all_subsys_list = getAllSubsystems()
        with open(self.file_name, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames= FIELDNAMES)
            if not self.file_exists:
                writer.writeheader()
            for subsystem in all_subsys_list:
                writer.writerow({'Subsystem': subsystem,
                            'Total Tests': 0, 
                            'Pass': 0,
                            'Fail': 0,
                            'Hang': 0})

    def find_summaries(self, subsystem_path):
        summary_paths = []

        if os.path.isfile(subsystem_path):
            if subsystem_path.endswith("_summary.log"):
                summary_paths.append(subsystem_path)
        
        elif os.path.isdir(subsystem_path):
            search_pattern = os.path.join(subsystem_path, "**", "*_summary.log")
            summary_paths = glob.glob(search_pattern, recursive=True)
        
        else:
            print(f"Warning: '{subsystem_path}' is not a valid file or directory.")
        
        return summary_paths

    def addSummary(self, summary_log):
        try:
            with open(summary_log, "r") as f:
                lines = f.readlines()
            
        except FileNotFoundError:
            print(f"Error: Log file not found at '{summary_log}'")
            return None
        
        ip, ext = os.path.splitext(os.path.basename(summary_log))
        ip = ip.replace("_summary", "")
        match = None
        for line in lines:
            match = SUMMARY_PATTERN.search(line.strip())
            if match: break
        if match:
            new_test, new_fail, new_ignore, new_hang, error_msg = map(int, match.groups())
            new_pass = new_test - new_fail - new_ignore - new_hang
            # Read existing CSV content
            all_rows= []
            row_found = False
            if os.path.isfile(self.file_name):
                with open(self.file_name, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    # Find the matching subsystem row
                    for row in reader:
                        if row['Subsystem'] == ip:
                            # Update the values by adding new stats to existing stats
                            row['Total Tests'] = int(row.get('Total Tests', 0)) + new_test
                            row['Pass'] = int(row.get('Pass', 0)) + new_pass
                            row['Fail'] = int(row.get('Fail', 0 )) + new_fail
                            row['Hang'] = int(row.get('Hang', 0)) + new_hang
                            row_found = True
                        
                        all_rows.append(row)
            
            if not row_found:
                new_row = {
                    'Subsystem': ip,
                    'Total Tests': new_test,
                    'Pass': new_pass,
                    'Fail': new_fail,
                    'Hang': new_hang
                }
                all_rows.append(new_row)

        with open(self.file_name, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames= FIELDNAMES)
            writer.writeheader()
            writer.writerows(all_rows)
        
        print(f"Updated stats for {ip}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "Summarizes provided subsystem summary logs into a CSV report."
    )
    parser.add_argument(
        "-l",
        "--log_summary", 
        type=str,
        help="Path to summary log (e.g. cpu_main_summary.log)",
        default = '/usr/local/google/home/chinmingryan/Documents/logs/mbu/test_command_output'
    )
    parser.add_argument(
        "-o",
        "--output_log",
        type=str,
        help="Output path for csv file",
        default = '/usr/local/google/home/chinmingryan/Documents/logs/mbu/test_command_output/report'
    )
    args = parser.parse_args()
    testClass = CSVSummary(args.output_log)
    summary_list = testClass.find_summaries(args.log_summary)
    for summary in summary_list:
        testClass.addSummary(summary)
