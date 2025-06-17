#!/usr/bin/env python3

import os
import sys
import argparse
import requests
import urllib3
# Suppress InsecureRequestWarning when verify=False is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import json
import subprocess
import base64
from concurrent.futures import ThreadPoolExecutor

# Constants
SHOCK_SERVER = "shock.mg-rast.org"

def load_auth(token=None, verbose=False):
    """Load authentication token from command line, environment variable, or auth file"""
    # Check command line token first (highest precedence)
    if token:
        if verbose:
            print("Using authentication token from command line")
        return token
    
    # Check environment variable next
    env_token = os.environ.get("SHOCK_AUTH_TOKEN")
    if env_token:
        if verbose:
            print("Using authentication token from SHOCK_AUTH_TOKEN environment variable")
        return env_token
    
    # Check auth files last
    auth_file_paths = [
        os.path.expanduser("~/.shock-auth.env"),
        "/usr/local/share/anl-seq-service/auth.env"
    ]
    
    for path in auth_file_paths:
        if os.path.exists(path):
            if verbose:
                print(f"Found auth file: {path}")
            with open(path, 'r') as f:
                for line in f:
                    if line.startswith("AUTH="):
                        if verbose:
                            print(f"Using authentication token from {path}")
                        return line.strip().split("=", 1)[1]
    
    # If no auth found, prompt user
    username = input("Enter shock username: ")
    password = input("Enter shock password: ")
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"mgrast {encoded_credentials}"

def get_run_folders(args):
    """Get list of run folders from args or file"""
    run_folders = []
    
    # Get run folders from command line arguments
    if args.run_folders:
        run_folders.extend(args.run_folders)
    
    # Get run folders from file
    if args.file:
        with open(args.file, 'r') as f:
            for line in f:
                folder = line.strip()
                if folder and not folder.startswith("#"):
                    run_folders.append(folder)
    
    # Validate run folders
    valid_run_folders = []
    for folder in run_folders:
        folder_path = os.path.join(args.directory, folder)
        if os.path.isdir(folder_path):
            if os.path.exists(os.path.join(folder_path, "RTAComplete.txt")):
                valid_run_folders.append(folder)
            else:
                print(f"Warning: {folder} is not a complete run folder (missing RTAComplete.txt)")
        else:
            print(f"Warning: {folder} is not a valid directory")
    
    return valid_run_folders

def find_fastq_files(run_folder_path):
    """Find all fastq files in a run folder"""
    # Use a more specific pattern to only match .fastq and .fastq.gz files
    cmd = f"find {run_folder_path} -name '*.fastq' -o -name '*.fastq.gz'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    files = result.stdout.strip().split('\n')
    # Filter out empty strings and non-fastq files
    return [f for f in files if f and (f.endswith('.fastq') or f.endswith('.fastq.gz'))]

def query_shock_fastq(run_folder_name, auth_token, verbose=False):
    """Query shock for fastq files with pagination"""
    all_nodes = []
    offset = 0
    limit = 25  # Default limit per response
    
    if verbose:
        print(f"Querying Shock for FASTQ files with project_id={run_folder_name}")
    
    while True:
        url = f"https://{SHOCK_SERVER}/node?query&type=run-folder-archive-fastq&project_id={run_folder_name}&offset={offset}&limit={limit}"
        headers = {"Authorization": auth_token}
        
        if verbose:
            print(f"Query URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()  # Raise exception for HTTP errors
            data = response.json()
            
            if verbose:
                print(f"Response status: {response.status_code}")
                print(f"Response data: {json.dumps(data, indent=2)[:500]}...")
            
            if "data" in data and data["data"]:
                all_nodes.extend(data["data"])
                if verbose:
                    print(f"Found {len(data['data'])} nodes, total so far: {len(all_nodes)}")
            else:
                if verbose:
                    print("No data found in response")
            
            # Check if we've retrieved all files
            if "total_count" in data and offset + limit >= data["total_count"]:
                if verbose:
                    print(f"Retrieved all {data['total_count']} nodes")
                break
            
            offset += limit
        except requests.exceptions.RequestException as e:
            print(f"Error querying shock for fastq files: {e}")
            if verbose:
                print(f"Full error: {str(e)}")
            return {"data": []}
    
    # Return a response-like object with all nodes
    return {"data": all_nodes}

def query_shock_sav(run_folder_name, auth_token, verbose=False):
    """Query shock for SAV files"""
    url = f"https://{SHOCK_SERVER}/node?query&type=run-folder-archive-sav&project_id={run_folder_name}"
    headers = {"Authorization": auth_token}
    
    if verbose:
        print(f"Querying Shock for SAV files with project_id={run_folder_name}")
        print(f"Query URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        
        if verbose:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {json.dumps(data, indent=2)[:500]}...")
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error querying shock for SAV files: {e}")
        if verbose:
            print(f"Full error: {str(e)}")
        return {"data": []}

def query_shock_raw(run_folder_name, auth_token, verbose=False):
    """Query shock for raw files"""
    url = f"https://{SHOCK_SERVER}/node?query&type=run-folder-archive-raw&project_id={run_folder_name}"
    headers = {"Authorization": auth_token}
    
    if verbose:
        print(f"Querying Shock for RAW files with project_id={run_folder_name}")
        print(f"Query URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        
        if verbose:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {json.dumps(data, indent=2)[:500]}...")
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error querying shock for raw files: {e}")
        if verbose:
            print(f"Full error: {str(e)}")
        return {"data": []}

def check_run_folder(run_folder_name, run_folder_dir, auth_token, check_sav=False, check_raw=False, verbose=False):
    """Check if a run folder and its files are uploaded to shock"""
    result = {
        "run_folder": run_folder_name,
        "fastq_files": {
            "total": 0,
            "uploaded": 0,
            "missing": [],
            "file_info": {}  # Will store file_name -> {path, parent_dir} mapping
        },
        "undetermined_files": {
            "status": "missing",
            "files_found": []
        }
    }
    
    # Check fastq files
    run_folder_path = os.path.join(run_folder_dir, run_folder_name)
    fastq_files = find_fastq_files(run_folder_path)
    result["fastq_files"]["total"] = len(fastq_files)
    
    # Store file info for each fastq file
    for fastq_file in fastq_files:
        file_name = os.path.basename(fastq_file)
        parent_dir = os.path.dirname(fastq_file)
        result["fastq_files"]["file_info"][file_name] = {
            "path": fastq_file,
            "parent_dir": parent_dir
        }
    
    # Check for Undetermined files with more flexible pattern matching
    r1_found = False
    r2_found = False
    undetermined_found = []
    
    for fastq_file in fastq_files:
        filename = os.path.basename(fastq_file)
        # Check if filename matches Undetermined*R1* pattern
        if filename.startswith("Undetermined_") and "_R1_" in filename:
            r1_found = True
            undetermined_found.append(filename)
        # Check if filename matches Undetermined*R2* pattern
        elif filename.startswith("Undetermined_") and "_R2_" in filename:
            r2_found = True
            undetermined_found.append(filename)
    
    # Update undetermined files status based on which files were found
    if r1_found and r2_found:
        result["undetermined_files"]["status"] = "present"
    elif r1_found or r2_found:
        result["undetermined_files"]["status"] = "partial"
    else:
        result["undetermined_files"]["status"] = "missing"
    
    result["undetermined_files"]["files_found"] = undetermined_found
    
    # Query shock for fastq files
    shock_fastq = query_shock_fastq(run_folder_name, auth_token, verbose)
    
    # Check if each fastq file is uploaded
    if "data" in shock_fastq and shock_fastq["data"]:
        # Get shock file names and normalize them
        shock_files = [node["file"]["name"] for node in shock_fastq["data"]]
        
        # Normalize shock file names by removing extensions
        shock_files_normalized = []
        for f in shock_files:
            # Remove .gz extension if present
            f_norm = f.replace('.gz', '')
            # Remove .fastq extension if present
            if f_norm.endswith('.fastq'):
                f_norm = f_norm[:-6]
            shock_files_normalized.append(f_norm)
        
        if verbose:
            print(f"Found {len(shock_files)} files in Shock")
            print(f"First few Shock files: {shock_files[:5]}")
            print(f"First few normalized Shock files: {shock_files_normalized[:5]}")
        
        # Process local files
        uploaded_count = 0
        missing_files = []
        
        # Debug: Print the first few local files
        if verbose:
            sample_local = [os.path.basename(f) for f in fastq_files[:5]]
            print(f"Sample local files: {sample_local}")
            
            # Print normalized versions
            sample_norm = []
            for f in sample_local:
                f_norm = f.replace('.gz', '')
                if f_norm.endswith('.fastq'):
                    f_norm = f_norm[:-6]
                sample_norm.append(f_norm)
            print(f"Sample normalized local files: {sample_norm}")
            
            # Check if any of these sample files match with shock files
            for i, f_norm in enumerate(sample_norm):
                if f_norm in shock_files_normalized:
                    print(f"Match found for {sample_local[i]}")
                else:
                    print(f"No match found for {sample_local[i]}")
                    # Print some close matches if any
                    close_matches = [sf for sf in shock_files_normalized if f_norm in sf or sf in f_norm]
                    if close_matches:
                        print(f"  Possible close matches: {close_matches[:5]}")
        
        # The issue might be with the file naming pattern
        # Let's try a different approach - extract just the sample ID part
        for fastq_file in fastq_files:
            file_name = os.path.basename(fastq_file)
            # Get the parent directory name
            # This is the directory where the fastq file is located
            parent_dir = os.path.basename(os.path.dirname(fastq_file))
            
            # Normalize local file name
            file_norm = file_name.replace('.gz', '')
            if file_norm.endswith('.fastq'):
                file_norm = file_norm[:-6]
            
            # Try to match by sample ID (first part before underscore)
            sample_id = file_norm.split('_')[0]
            
            # Check if any shock file contains this sample ID
            found = False
            for shock_norm in shock_files_normalized:
                if shock_norm.startswith(sample_id + '_'):
                    found = True
                    break
            
            if found:
                uploaded_count += 1
            else:
                missing_files.append(file_name)
        
        result["fastq_files"]["uploaded"] = uploaded_count
        result["fastq_files"]["missing"] = missing_files
    else:
        # If no files found in Shock, all local files are missing
        result["fastq_files"]["missing"] = [os.path.basename(f) for f in fastq_files]
    
    # Check SAV files if requested
    if check_sav:
        result["sav_files"] = {"status": "not_checked"}
        shock_sav = query_shock_sav(run_folder_name, auth_token, verbose)
        if "data" in shock_sav and shock_sav["data"]:
            result["sav_files"] = {"status": "uploaded"}
        else:
            result["sav_files"] = {"status": "missing"}
    
    # Check raw files if requested
    if check_raw:
        result["raw_files"] = {"status": "not_checked"}
        shock_raw = query_shock_raw(run_folder_name, auth_token, verbose)
        if "data" in shock_raw and shock_raw["data"]:
            result["raw_files"] = {"status": "uploaded"}
        else:
            result["raw_files"] = {"status": "missing"}
    
    return result

def generate_report(results, output_file=None, directory=None):
    """Generate report of run folders and their upload status"""
    # Define undetermined report filename based on output_file
    undetermined_report_file = None
    if output_file:
        # Get the base filename without extension
        base_name = os.path.splitext(output_file)[0]
        undetermined_report_file = f"{base_name}_undetermined.tsv"
    # Calculate summary statistics
    total_run_folders = len(results)
    complete_uploads = 0
    partial_uploads = 0
    missing_uploads = 0
    
    for result in results:
        if result["fastq_files"]["total"] == result["fastq_files"]["uploaded"]:
            complete_uploads += 1
        elif result["fastq_files"]["uploaded"] > 0:
            partial_uploads += 1
        else:
            missing_uploads += 0 if result["fastq_files"]["total"] == 0 else 1
    
    # Generate summary report for console output
    summary = []
    summary.append("# Shock Upload Status Summary")
    summary.append("")
    summary.append(f"Total run folders: {total_run_folders}")
    summary.append(f"Complete uploads: {complete_uploads}")
    summary.append(f"Partial uploads: {partial_uploads}")
    summary.append(f"Missing uploads: {missing_uploads}")
    summary.append("")
    
    for result in results:
        complete_status = "Complete" if result["fastq_files"]["total"] == result["fastq_files"]["uploaded"] else "Partial" if result["fastq_files"]["uploaded"] > 0 else "Missing"
        summary.append(f"{result['run_folder']}: {result['fastq_files']['uploaded']}/{result['fastq_files']['total']} files uploaded\t{complete_status}")
    
    # Print summary to console
    summary_text = "\n".join(summary)
    print(summary_text)
    
    # Generate detailed TSV report for missing files
    if output_file:
        with open(output_file, 'w') as f:
            # Write TSV header
            f.write("run-folder-name\tdirname of missing fastq file\tmissing fastq file\n")
            
            # Write missing files data
            for result in results:
                run_folder = result["run_folder"]
                
                for missing_file in result["fastq_files"]["missing"]:
                    # Use the stored file info instead of searching again
                    if "file_info" in result["fastq_files"] and missing_file in result["fastq_files"]["file_info"]:
                        file_info = result["fastq_files"]["file_info"][missing_file]
                        # dirname = os.path.basename(file_info["parent_dir"])
                        # split the path and return at least the last two components
                        dirname_parts = file_info["parent_dir"].split(os.sep)
                        if len(dirname_parts) > 1:
                            dirname = os.path.join(dirname_parts[-2], dirname_parts[-1])
                        else:
                            dirname = dirname_parts[-1]

                        f.write(f"{run_folder}\t{dirname}\t{missing_file}\n")
                    else:
                        # Fallback if file info is not available
                        f.write(f"{run_folder}\t(unknown)\t{missing_file}\n")
    
    # Generate report for undetermined files
    if undetermined_report_file:
        with open(undetermined_report_file, 'w') as f:
            # Write TSV header
            f.write("run-folder-name\tundetermined_status\tfiles_found\n")
            
            # Write undetermined files status for each run folder
            for result in results:
                run_folder = result["run_folder"]
                status = result.get("undetermined_files", {}).get("status", "unknown")
                files_found = ",".join(result.get("undetermined_files", {}).get("files_found", []))
                
                f.write(f"{run_folder}\t{status}\t{files_found}\n")
        
        print(f"\nUndetermined files report written to: {undetermined_report_file}")

def main():
    parser = argparse.ArgumentParser(description="Check if run folders and fastq files are uploaded to shock")
    parser.add_argument("-d", "--directory", required=True, help="Directory containing run folders")
    parser.add_argument("-r", "--run-folders", nargs="+", help="Space-separated list of run folder names")
    parser.add_argument("-f", "--file", help="File containing list of run folder names (one per line)")
    parser.add_argument("-s", "--check-sav", action="store_true", help="Also check for SAV files")
    parser.add_argument("-a", "--check-raw", action="store_true", help="Also check for raw files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-o", "--output", help="Write report to file")
    parser.add_argument("-t", "--token", help="Authentication token for shock server")
    args = parser.parse_args()
    
    # Validate arguments
    if not args.run_folders and not args.file:
        parser.error("Either --run-folders or --file must be provided")
    
    # Load authentication
    auth_token = load_auth(args.token, args.verbose)
    
    # Get run folders
    run_folders = get_run_folders(args)
    
    if not run_folders:
        print("No valid run folders found")
        sys.exit(1)
    
    # Check each run folder
    results = []
    for folder in run_folders:
        if args.verbose:
            print(f"Checking {folder}...")
        result = check_run_folder(folder, args.directory, auth_token, args.check_sav, args.check_raw, args.verbose)
        results.append(result)
    
    # Generate report
    generate_report(results, args.output, args.directory)

if __name__ == "__main__":
    main()