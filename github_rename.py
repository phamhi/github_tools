#!/usr/bin/env python3

"""
GitHub Repository Renaming Tool
Renames GitHub repositories based on input file specifications.
"""

import os
import sys
import logging
import argparse
import urllib3
import csv
from typing import List, Tuple, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class GitHubAPIClient:
    """Handles GitHub API interactions with retry logic and authentication.
    
    Args:
        token (str): GitHub personal access token for authentication
        org (str): GitHub organization name
    """

    def __init__(self, token: str, org: str):
        self.token = token
        self.org = org
        self.session = self._create_session()
        self.base_url = "https://api.github.com"

    def _create_session(self) -> requests.Session:
        """Creates a session with retry logic and headers."""
        session = requests.Session()

        # Disable SSL verification
        session.verify = False

        # Suppress SSL verification warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)

        # Set headers for GitHub API
        session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Latest-Commit-Fetcher"
        })

        return session

    def get_latest_commit(self, repo_name: str) -> Optional[dict]:
        """Fetches the latest commit for a repository.
        
        Args:
            repo_name (str): Name of the repository to fetch commits from
            
        Returns:
            Optional[dict]: Latest commit information or None if not found/error
        """
        try:
            url = f"{self.base_url}/repos/{self.org}/{repo_name}/commits"
            response = self.session.get(url, params={"per_page": 1})

            if response.status_code == 404:
                logging.error(f"Repository not found: {repo_name}")
                return None

            response.raise_for_status()
            commits = response.json()

            if not commits:
                logging.error(f"No commits found in repository: {repo_name}")
                return None

            return commits[0]

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching commits for {repo_name}: {str(e)}")
            return None

    def get_repo_details(self, repo_name: str) -> Optional[dict]:
        """Fetches repository details including creation date.
        
        Args:
            repo_name (str): Name of the repository to fetch details for
            
        Returns:
            Optional[dict]: Repository information or None if not found/error
        """
        try:
            url = f"{self.base_url}/repos/{self.org}/{repo_name}"
            response = self.session.get(url)

            if response.status_code == 404:
                logging.error(f"Repository not found: {repo_name}")
                return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching repository details for {repo_name}: {str(e)}")
            return None

    def get_latest_pr(self, repo_name: str) -> Optional[dict]:
        """Fetches the latest pull request for a repository.
        
        Args:
            repo_name (str): Name of the repository to fetch PRs from
            
        Returns:
            Optional[dict]: Latest PR information or None if not found/error
        """
        try:
            url = f"{self.base_url}/repos/{self.org}/{repo_name}/pulls"
            response = self.session.get(url, params={"state": "all", "sort": "created", "direction": "desc", "per_page": 1})

            if response.status_code == 404:
                logging.error(f"Repository not found: {repo_name}")
                return None

            response.raise_for_status()
            prs = response.json()

            if not prs:
                logging.debug(f"No PRs found in repository: {repo_name}")
                return None

            return prs[0]

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching PRs for {repo_name}: {str(e)}")
            return None

    def get_repo_name(self, repo_name: str) -> Optional[str]:
        """Gets the current name of a repository.
        
        Args:
            repo_name (str): Name of the repository to check
            
        Returns:
            Optional[str]: Current repository name or None if not found
        """
        try:
            url = f"{self.base_url}/repos/{self.org}/{repo_name}"
            response = self.session.get(url)
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json().get('name')

        except requests.exceptions.RequestException as e:
            logging.error(f"Error checking repository {repo_name}: {str(e)}")
            return None

    def does_repo_exist(self, repo_name: str) -> bool:
        """Checks if a repository exists.
        
        Args:
            repo_name (str): Name of the repository to check
            
        Returns:
            bool: True if repository exists, False otherwise
        """
        try:
            url = f"{self.base_url}/repos/{self.org}/{repo_name}"
            response = self.session.get(url)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def rename_repository(self, old_name: str, new_name: str) -> Tuple[bool, Optional[str]]:
        """Renames a repository.
        
        Args:
            old_name (str): Current name of the repository
            new_name (str): New name for the repository
            
        Returns:
            Tuple[bool, Optional[str]]: (Success status, Error message if any)
        """
        try:
            # First check if the source repository exists
            current_name = self.get_repo_name(old_name)
            if current_name is None:
                error_msg = f"Source repository not found: {old_name}"
                logging.error(error_msg)
                return False, error_msg
                
            # Check if the repository is already renamed - consider this a success
            if current_name == new_name:
                return True, f"Repository is already named '{new_name}'"

            # Check if target name already exists
            if self.does_repo_exist(new_name):
                error_msg = f"Cannot rename: target repository '{new_name}' already exists"
                logging.error(error_msg)
                return False, error_msg

            url = f"{self.base_url}/repos/{self.org}/{old_name}"
            response = self.session.patch(url, json={"name": new_name}, allow_redirects=True)
            
            if response.status_code == 404:
                error_msg = "Repository not found"
                logging.error(error_msg)
                return False, error_msg

            response.raise_for_status()
            return True, None

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logging.error(error_msg)
            return False, error_msg

def validate_environment() -> tuple[str, str]:
    """Validates and returns required environment variables.
    
    Returns:
        tuple[str, str]: A tuple containing (github_token, github_org)
        
    Raises:
        ValueError: If required environment variables are not set
    """
    token = os.getenv("GITHUB_TOKEN")
    org = os.getenv("GITHUB_ORG")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    if not org:
        raise ValueError("GITHUB_ORG environment variable is not set")

    return token, org

def read_repo_list(file_path: str) -> List[str]:
    """Reads repository names from a file.
    
    Args:
        file_path (str): Path to the file containing repository names
        
    Returns:
        List[str]: List of repository names
        
    Raises:
        SystemExit: If file cannot be read
    """
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except IOError as e:
        logging.error(f"Error reading input file: {str(e)}")
        sys.exit(1)

def read_rename_pairs(file_path: str) -> List[Tuple[str, str]]:
    """Reads repository rename pairs from a CSV file.
    
    Args:
        file_path (str): Path to the CSV file containing old and new names
        
    Returns:
        List[Tuple[str, str]]: List of (old_name, new_name) pairs
        
    Raises:
        SystemExit: If file cannot be read
    """
    try:
        pairs = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pairs.append((row['REPO_NAME'], row['REPO_NEW_NAME']))
        return pairs
    except IOError as e:
        logging.error(f"Error reading input file: {str(e)}")
        sys.exit(1)

def write_results(file_path: str, results: List[Tuple[str, str, str, Optional[str]]]):
    """Writes renaming results to a log file.
    
    Args:
        file_path (str): Path to the output log file
        results: List of (old_name, new_name, status, log) tuples
    """
    try:
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['REPO_NAME', 'REPO_NEW_NAME', 'STATUS', 'LOG'])
            for result in results:
                writer.writerow(result)
    except IOError as e:
        logging.error(f"Error writing to log file: {str(e)}")

def process_repo(client: GitHubAPIClient, repo_name: str) -> None:
    """Processes a single repository and prints commit and PR information.
    
    Args:
        client (GitHubAPIClient): Initialized GitHub API client
        repo_name (str): Name of the repository to process
    """
    commit_info = client.get_latest_commit(repo_name)
    repo_info = client.get_repo_details(repo_name)
    pr_info = client.get_latest_pr(repo_name)

    if commit_info and repo_info:
        # Extract commit information
        commit = commit_info['commit']
        sha = commit_info['sha']
        created_at = repo_info['created_at']
        # created_by = repo_info['owner']['login']

        committer = ''
        author = ''
        # Handle null committer cases
        if commit_info.get('committer') is not None:
            committer = commit_info['committer'].get('login', 'Unknown')
            date = commit['committer'].get('date', '')
        else:
            # Fallback to committer name from commit object
            committer = commit['committer'].get('name', 'Unknown').replace(',', '-').replace(' ', '')
            date = commit['committer'].get('date', '')

        # Handle null author cases
        if commit_info.get('author') is not None:
            author = commit_info['author'].get('login', 'Unknown')
        else:
            # Fallback to author name from commit object
            author = commit['author'].get('name', 'Unknown').replace(',', '-').replace(' ', '')

        # Add PR information
        pr_created_at = "N/A"
        pr_author = "N/A"
        pr_url = "N/A"
        if pr_info:
            pr_created_at = pr_info['created_at']
            pr_author = pr_info['user']['login'] if pr_info['user'] else "Unknown"
            pr_url = pr_info['html_url']

        repo_url = f"https://github.com/{client.org}/{repo_name}"
        print(f"{repo_url},{created_at},{date},{committer},{author},{sha},{pr_created_at},{pr_author},{pr_url}")

def main():
    """Main function to handle repository renaming."""
    parser = argparse.ArgumentParser(description="Rename GitHub repositories")
    parser.add_argument("--input", "-i", required=True, help="Input CSV file with repository names")
    parser.add_argument("--output", "-o", required=True, help="Output log file path")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    try:
        # Validate environment
        token, org = validate_environment()
        client = GitHubAPIClient(token, org)

        # Read rename pairs
        rename_pairs = read_rename_pairs(args.input)
        results = []

        # Process each repository
        for old_name, new_name in rename_pairs:
            logging.info(f"Renaming repository: {old_name} -> {new_name}")
            success, message = client.rename_repository(old_name, new_name)
            
            status = "OK" if success else "FAILED"
            # Only include error messages in the log, not success messages
            log_message = None if success else message
            results.append((old_name, new_name, status, log_message))

        # Write results to the specified output file
        write_results(args.output, results)

    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()