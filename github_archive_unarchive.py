import os
import sys
import requests
import argparse
import logging
from typing import List, Tuple, Optional, Dict, Any
import urllib3
import time
import json

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    pass

def setup_logging(debug: bool) -> None:
    """Configure logging with appropriate level and format.

    Args:
        debug: If True, sets logging level to DEBUG, otherwise INFO
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def parse_args() -> argparse.Namespace:
    """Parse and validate command line arguments.

    Returns:
        Namespace containing parsed command line arguments
    
    Raises:
        SystemExit: If required arguments are missing
    """
    parser = argparse.ArgumentParser(description='Archive or unarchive GitHub repositories')
    parser.add_argument('-a', '--action', required=True, choices=['archive', 'unarchive'],
                       help='Action to perform: archive or unarchive')
    parser.add_argument('repos', nargs='*', help='List of repositories to process')
    parser.add_argument('-i', '--input', help='Input file containing list of repositories')
    parser.add_argument('-o', '--output', help='Output csv file for results')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    if not args.repos and not args.input:
        parser.error("Either specify repositories as arguments or provide an input file")

    setup_logging(args.debug)
    return args

def get_repositories(args: argparse.Namespace) -> List[str]:
    """Extract repository names from command line arguments and input file.

    Args:
        args: Parsed command line arguments

    Returns:
        List of repository names to process

    Raises:
        SystemExit: If input file cannot be read
    """
    repos = args.repos
    if args.input:
        try:
            with open(args.input, 'r') as f:
                file_repos = [line.strip() for line in f if line.strip()]
                repos.extend(file_repos)
        except IOError as e:
            logging.error(f"Error reading input file: {e}")
            sys.exit(1)
    
    logging.debug(f"Processing repositories: {repos}")
    return repos

def validate_response(response: requests.Response, operation: str) -> Dict[str, Any]:
    """Validate API response and extract JSON data.

    Args:
        response: Response object from requests
        operation: Description of the operation for error messages

    Returns:
        Parsed JSON response data

    Raises:
        GitHubAPIError: If response status is unexpected or JSON parsing fails
    """
    try:
        if response.status_code == 404:
            raise GitHubAPIError("Repository not found")
        elif response.status_code == 403:
            raise GitHubAPIError("API rate limit exceeded or insufficient permissions")
        elif response.status_code not in (200, 201):
            raise GitHubAPIError(f"API request failed: {response.status_code}")
        
        return response.json()
    except json.JSONDecodeError as e:
        raise GitHubAPIError(f"Failed to parse API response: {e}")

def get_repository_status(url: str, headers: Dict[str, str]) -> Tuple[bool, str]:
    """Check if repository is already archived.

    Args:
        url: GitHub API URL for the repository
        headers: Request headers including authentication

    Returns:
        Tuple of (is_archived, status_string) where status_string is ARCHIVED/UNARCHIVED/UNKNOWN

    Raises:
        GitHubAPIError: If API request fails
    """
    try:
        response = requests.get(url, headers=headers, verify=False)
        data = validate_response(response, "status check")
        is_archived = data.get('archived', False)
        status = "ARCHIVED" if is_archived else "UNARCHIVED"
        return is_archived, status
    except requests.RequestException as e:
        raise GitHubAPIError(f"Failed to get repository status: {e}")

def archive_repository(repo: str, action: str) -> Tuple[str, str, str]:
    """Archive or unarchive a GitHub repository.

    Args:
        repo: Name of the repository to process
        action: Either 'archive' or 'unarchive'

    Returns:
        Tuple of (repository_name, result_status, current_status)
        where result_status is either "OK" or "FAILED,<error_message>"
        and current_status is ARCHIVED/UNARCHIVED/UNKNOWN
    """
    token = os.getenv('GITHUB_TOKEN')
    org = os.getenv('GITHUB_ORG')
    
    if not token or not org:
        logging.error("GITHUB_TOKEN and GITHUB_ORG environment variables must be set")
        sys.exit(1)

    headers: Dict[str, str] = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28'
    }

    url = f'https://api.github.com/repos/{org}/{repo}'
    logging.debug(f"Checking repository status: {url}")

    try:
        # Check current archive status
        is_archived, current_status = get_repository_status(url, headers)
        should_archive = action == 'archive'
        
        # Skip if already in desired state
        if is_archived == should_archive:
            status = "archived" if is_archived else "unarchived"
            logging.debug(f"Repository {repo} is already {status}")
            return repo, "OK", current_status

        logging.debug(f"{action.capitalize()}ing repository: {url}")
        response = requests.patch(url, headers=headers, json={'archived': should_archive}, verify=False)
        validate_response(response, action)
        final_status = "ARCHIVED" if should_archive else "UNARCHIVED"
        return repo, "OK", final_status
        
    except GitHubAPIError as e:
        return repo, f"ERROR:{str(e)}", "UNKNOWN"
    except requests.RequestException as e:
        return repo, f"ERROR:network error: {str(e)}", "UNKNOWN"

def write_results(results: List[Tuple[str, str, str]], output_file: Optional[str] = None) -> None:
    """Write archiving results to output file.

    Args:
        results: List of (repository_name, result_status, current_status) tuples
        output_file: Path to output file, or None to skip writing

    Raises:
        SystemExit: If output file cannot be written
    """
    if not output_file:
        return
    
    try:
        with open(output_file, 'a') as f:
            for repo, result, status in results:
                f.write(f"{repo},{status},{result}\n")
    except IOError as e:
        logging.error(f"Error writing to output file: {e}")
        sys.exit(1)

def main():
    args = parse_args()
    repos = get_repositories(args)
    
    # Initialize output file with header if specified
    if args.output:
        try:
            with open(args.output, 'w') as f:
                f.write("REPO,STATUS,RESULT\n")
        except IOError as e:
            logging.error(f"Error initializing output file: {e}")
            sys.exit(1)
    
    print("REPO,STATUS,RESULT")
    
    results = []
    last_write_time = time.time()
    FLUSH_INTERVAL = 5  # seconds
    
    try:
        for repo in repos:
            result = archive_repository(repo, args.action)
            results.append(result)
            print(f"{result[0]},{result[2]},{result[1]}")
            logging.debug(f"Repository {repo} {args.action} result: {result[1]} (status: {result[2]})")

            current_time = time.time()
            if args.output and current_time - last_write_time >= FLUSH_INTERVAL and results:
                write_results(results, args.output)
                results = []
                last_write_time = current_time

    except KeyboardInterrupt:
        logging.info("Caught keyboard interrupt, flushing remaining results...")
        if results:
            if args.output:
                write_results(results, args.output)
            logging.info("Results saved, exiting...")
        sys.exit(0)

    # Write any remaining results
    if results and args.output:
        write_results(results, args.output)
    logging.debug("Archive process completed")

if __name__ == "__main__":
    main()