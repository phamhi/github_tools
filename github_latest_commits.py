#!/usr/bin/env python3

"""
GitHub Repository Latest Commit Fetcher
Retrieves the latest commit information for specified GitHub repositories.
"""

import os
import sys
import logging
import argparse
import urllib3
from typing import List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class GitHubAPIClient:
    """Handles GitHub API interactions with retry logic and authentication."""

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
        """
        Fetches the latest commit for a repository.
        Returns None if repository doesn't exist or error occurs.
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

def validate_environment() -> tuple[str, str]:
    """Validates and returns required environment variables."""
    token = os.getenv("GITHUB_TOKEN")
    org = os.getenv("GITHUB_ORG")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    if not org:
        raise ValueError("GITHUB_ORG environment variable is not set")

    return token, org

def read_repo_list(file_path: str) -> List[str]:
    """Reads repository names from a file."""
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except IOError as e:
        logging.error(f"Error reading input file: {str(e)}")
        sys.exit(1)

def process_repo(client: GitHubAPIClient, repo_name: str) -> None:
    """Processes a single repository and prints commit information."""
    commit_info = client.get_latest_commit(repo_name)

    if commit_info:
        # Extract commit information
        commit = commit_info['commit']
        sha = commit_info['sha']

        # Handle null committer/author cases
        if commit_info.get('committer') is not None:
            username = commit_info['committer'].get('login', 'Unknown')
            date = commit['committer'].get('date', '')
        elif commit_info.get('author') is not None:
            username = commit_info['author'].get('login', 'Unknown')
            date = commit['author'].get('date', '')
        else:
            # Fallback to committer name from commit object
            username = commit['committer'].get('name', 'Unknown').replace(' ', '_')
            date = commit['committer'].get('date', '')

        repo_url = f"https://github.com/{client.org}/{repo_name}"
        print(f"{repo_url},{username},{date},{sha}")

def main():
    """Main function to handle script execution."""
    parser = argparse.ArgumentParser(description="Fetch latest commit information from GitHub repositories")
    parser.add_argument("repos", nargs='*', help="Repository names")
    parser.add_argument("--input", "-i", help="File containing repository names")
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

        # Process repositories
        if args.input:
            repos = read_repo_list(args.input)
        elif args.repos:
            repos = args.repos
        else:
            parser.error("Either provide repository names as arguments or use --input file")

        if repos:
            print ("GIT URL,Committer,Commit Date,Commit ID")

        for repo in repos:
            process_repo(client, repo)

    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()