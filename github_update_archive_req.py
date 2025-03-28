#!/usr/bin/env python3

"""
GitHub Repository Property Updater
--------------------------------
Unarchives GitHub repositories, updates their request number property, and re-archives them.
Supports both single repository and batch processing via CSV files.

Required environment variables:
    GITHUB_TOKEN: Personal access token with repository permissions
    GITHUB_ORG: GitHub organization name
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, Optional, List, NamedTuple
from collections import OrderedDict

import requests
from requests.exceptions import RequestException
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Type definitions
GitHubRepo = Dict[str, any]
ProcessingResult = Dict[str, bool]

class GitHubConfig:
    """Configuration for GitHub API access"""
    def __init__(
        self,
        token: str,
        org: str,
        base_url: str = "https://api.github.com",
        verify_ssl: bool = True,
        api_version: str = "2022-11-28"
    ):
        self.token = token
        self.org = org
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.api_version = api_version

    @property
    def headers(self) -> Dict[str, str]:
        """Return headers required for GitHub API calls"""
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": self.api_version,
        }

class ProcessingError(Exception):
    """Custom exception for repository processing errors"""
    pass

class GitHubRepoManager:
    """Manages GitHub repository operations"""
    
    def __init__(self, config: GitHubConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an HTTP request to GitHub API with error handling"""
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.config.headers,
                verify=self.config.verify_ssl,
                **kwargs
            )
            response.raise_for_status()
            return response
        except RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            raise ProcessingError(f"GitHub API request failed: {str(e)}")

    def get_repo(self, repo_name: str) -> Optional[GitHubRepo]:
        """Get repository information"""
        url = f"{self.config.base_url}/repos/{self.config.org}/{repo_name}"
        self.logger.debug(f"Getting repo info: {url}")
        
        try:
            response = self._make_request("GET", url)
            return response.json()
        except ProcessingError:
            return None

    def set_archive_state(self, repo_name: str, archived: bool) -> bool:
        """Archive or unarchive a repository"""
        url = f"{self.config.base_url}/repos/{self.config.org}/{repo_name}"
        action = "archive" if archived else "unarchive"
        self.logger.debug(f"Attempting to {action} repo: {repo_name}")
        
        try:
            response = self._make_request(
                "PATCH",
                url,
                json={"archived": archived}
            )
            result = response.json()
            if result.get("archived") == archived:
                self.logger.info(f"Successfully {action}d repo: {repo_name}")
                return True
            return False
        except ProcessingError:
            return False

    def update_request_number(self, repo_name: str, request_num: str) -> bool:
        """Update the request-num custom property"""
        url = f"{self.config.base_url}/repos/{self.config.org}/{repo_name}/properties/values"
        self.logger.debug(f"Updating request number for repo: {repo_name}")
        
        try:
            response = self._make_request(
                "PATCH",
                url,
                json={
                    "properties": [
                        {
                            "property_name": "request-num",
                            "value": request_num
                        }
                    ]
                }
            )
            return response.status_code == 204
        except ProcessingError:
            return False

class RepoProcessor:
    """Handles the repository processing workflow"""
    
    def __init__(self, github: GitHubRepoManager):
        self.github = github
        self.logger = logging.getLogger(__name__)

    def process_repo(self, repo_name: str, request_num: str) -> bool:
        """Process a single repository"""
        try:
            # Get repository info
            repo = self.github.get_repo(repo_name)
            if not repo:
                self.logger.error(f"Repository not found: {repo_name}")
                return False

            # Unarchive if necessary
            if repo.get("archived", False):
                if not self.github.set_archive_state(repo_name, False):
                    return False

            # Update request number
            if not self.github.update_request_number(repo_name, request_num):
                return False

            # Re-archive
            if not self.github.set_archive_state(repo_name, True):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error processing repo {repo_name}: {str(e)}")
            return False

def process_input_file(file_path: Path) -> OrderedDict:
    """Process input CSV file containing repository names"""
    result = OrderedDict()
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.isupper() or line.startswith('#'):
                    continue
                    
                parts = line.split(',', 1)
                repo_name = parts[0].strip()
                if repo_name:
                    result[repo_name] = parts[1].strip() if len(parts) > 1 else ''
                    
        return result
    except Exception as e:
        logging.error(f"Error processing input file: {str(e)}")
        return OrderedDict()

def write_output_file(file_path: Path, results: ProcessingResult):
    """Write processing results to CSV file"""
    try:
        with open(file_path, 'w') as f:
            f.write('REPO_NAME,RUN_OK\n')
            for repo_name, success in results.items():
                f.write(f'{repo_name},{success}\n')
    except Exception as e:
        logging.error(f"Error writing output file: {str(e)}")

def setup_logging(level: int) -> None:
    """Configure logging"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Update GitHub repository request numbers with unarchive/re-archive support.'
    )
    
    parser.add_argument(
        '--debug',
        help='Enable debug logging',
        action='store_const',
        dest='log_level',
        const=logging.DEBUG,
        default=logging.INFO,
    )
    
    parser.add_argument(
        '-i', '--input-file',
        help='CSV file containing list of repositories to process',
        type=Path,
    )
    
    parser.add_argument(
        '-o', '--output-file',
        help='CSV file to write results to',
        type=Path,
    )
    
    parser.add_argument(
        '-r', '--request-num',
        help='Request number to set',
        required=True,
    )
    
    parser.add_argument(
        'repo_name',
        nargs='?',
        help='Single repository to process',
        default='',
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Validate environment variables
    token = os.getenv('GITHUB_TOKEN')
    org = os.getenv('GITHUB_ORG')
    
    if not token or not org:
        logger.error("GITHUB_TOKEN and GITHUB_ORG environment variables must be set")
        sys.exit(1)
    
    # Initialize GitHub manager
    config = GitHubConfig(token=token, org=org, verify_ssl=False)
    github = GitHubRepoManager(config)
    processor = RepoProcessor(github)
    
    # Determine repositories to process
    repos = OrderedDict()
    if args.input_file:
        repos = process_input_file(args.input_file)
        if not repos:
            logger.error("No repositories found in input file")
            sys.exit(1)
    elif args.repo_name:
        repos[args.repo_name] = args.request_num
    else:
        logger.error("Either repository name or input file must be specified")
        sys.exit(1)
    
    # Process repositories
    results = OrderedDict()
    for repo_name in repos:
        logger.info(f"Processing repository: {repo_name}")
        success = processor.process_repo(repo_name, args.request_num)
        results[repo_name] = success
        
    # Write results if output file specified
    if args.output_file:
        write_output_file(args.output_file, results)
        
    # Exit with error if any repository failed
    if not all(results.values()):
        sys.exit(1)

if __name__ == "__main__":
    main()