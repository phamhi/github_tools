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

    def get_repo_details(self, repo_name: str) -> Optional[dict]:
        """Fetches repository details including creation date."""
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
        """Fetches the latest pull request for a repository."""
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
    """Processes a single repository and prints commit and PR information."""
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
            print("GIT URL,Repo Created At,Latest Commit Date,Committer,Commit Author,Latest Commit ID,Latest PR Date,PR Author,PR URL")

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