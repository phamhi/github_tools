import os
import sys
import requests
import argparse
import logging
from datetime import datetime
import json
import urllib3

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def setup_logging(debug=False):
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Fetch GitHub Personal Access Token information')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--stdout', action='store_true', help='Print output to stdout')
    parser.add_argument('-o', '--output-file', help='Output CSV file path')
    parser.add_argument('-j', '--json', help='Output JSON file path')
    args = parser.parse_args()
    
    # Validate that at least one output option is selected
    if not args.stdout and not args.output_file and not args.json:
        parser.error("At least one output option (--stdout, --output-file, or --json) must be specified")
    
    setup_logging(args.debug)
    return args

def check_env_vars():
    """Verify required environment variables are set."""
    logging.debug("Checking environment variables...")
    token = os.getenv('GITHUB_TOKEN')
    org = os.getenv('GITHUB_ORG')
    
    if not token or not org:
        logging.error(f"Missing vars - token: {'set' if token else 'missing'}, org: {'set' if org else 'missing'}")
        print("Error: GITHUB_TOKEN and GITHUB_ORG environment variables must be set", file=sys.stderr)
        sys.exit(1)
    
    logging.debug("Environment variables verified successfully")
    return token, org

def get_all_credentials(token, org):
    """Fetch all credential authorizations from GitHub API."""
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    
    all_credentials = []
    page = 1
        
    while True:
        url = f'https://api.github.com/orgs/{org}/credential-authorizations'
        logging.debug(f"Fetching page {page} from {url}")
        
        response = requests.get(url, headers=headers, params={'page': page, 'per_page': 100}, verify=False)
        
        if response.status_code != 200:
            logging.error(f"API request failed - Status: {response.status_code}")
            logging.error(f"Response: {response.text}")
            print(f"Error: API request failed with status {response.status_code}", file=sys.stderr)
            print(response.text, file=sys.stderr)
            sys.exit(1)
            
        data = response.json()
        if not data:  # No more pages
            logging.debug("No more pages to fetch")
            break
            
        logging.debug(f"Retrieved {len(data)} credentials from page {page}")
        all_credentials.extend(data)
        page += 1
    
    logging.info(f"Total credentials retrieved: {len(all_credentials)}")
    return all_credentials

def write_output(credentials, output_file=None, write_stdout=False):
    """Write credentials data to specified outputs."""
    csv_lines = ["login,credential_type,credential_authorized_at,credential_accessed_at,authorized_credential_expires_at,authorized_credential_note"]
    
    for cred in credentials:
        line = f"{cred.get('login', '')},{cred.get('credential_type', '')}," \
               f"{cred.get('credential_authorized_at', '')},{cred.get('credential_accessed_at', '')}," \
               f"{cred.get('authorized_credential_expires_at', '')},{cred.get('authorized_credential_note', '')}"
        csv_lines.append(line)
    
    if write_stdout:
        for line in csv_lines:
            print(line)
    
    if output_file:
        logging.info(f"Writing output to file: {output_file}")
        try:
            with open(output_file, 'w') as f:
                for line in csv_lines:
                    f.write(line + '\n')
        except IOError as e:
            logging.error(f"Error writing to file: {e}")
            sys.exit(1)

def write_json_output(credentials, json_file):
    """Write complete credentials data to JSON file without any modifications."""
    logging.info(f"Writing complete JSON output to file: {json_file}")
    try:
        with open(json_file, 'w') as f:
            # Save complete response data with proper formatting
            json.dump(credentials, f, indent=2, sort_keys=False)
    except IOError as e:
        logging.error(f"Error writing to JSON file: {e}")
        sys.exit(1)

def main():
    """Main function to fetch and display GitHub credential information."""
    args = parse_args()
    logging.info("Starting GitHub credential fetch...")
    
    token, org = check_env_vars()
    credentials = get_all_credentials(token, org)
    
    if args.json:
        write_json_output(credentials, args.json)
    write_output(credentials, args.output_file, args.stdout)
    logging.info("Process completed successfully")

if __name__ == "__main__":
    main()