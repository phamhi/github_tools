#!/usr/bin/env python3

"""
GitHub Actions Permissions Checker
----
Checks GitHub Actions permissions for repositories in an organization.
Exports data to CSV format.

Required environment variables:
    GITHUB_TOKEN: Personal access token with repository permissions
    GITHUB_ORG: GitHub organization name
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

import requests
import pandas as pd
from requests.exceptions import RequestException
from urllib3.exceptions import InsecureRequestWarning
import csv
import sys
import time
from datetime import datetime

# Suppress insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

@dataclass
class GitHubConfig:
    """Configuration for GitHub API access"""
    token: str
    org: str
    base_url: str = "https://api.github.com"
    verify_ssl: bool = True
    api_version: str = "2022-11-28"

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": self.api_version,
        }

class ProcessingError(Exception):
    """Custom exception for repository processing errors"""
    pass

class GitHubActionsChecker:
    """Checks GitHub Actions permissions for repositories"""

    def __init__(self, config: GitHubConfig, show_rate_limit: bool = False):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.last_check_time = 0
        self.check_interval = 5  # Check rate limit every 5 seconds
        self.show_rate_limit = show_rate_limit

    def _check_rate_limit(self) -> None:
        """Check and log GitHub API rate limit information"""
        current_time = time.time()
        if current_time - self.last_check_time >= self.check_interval:
            url = f"{self.config.base_url}/rate_limit"
            try:
                response = requests.get(
                    url=url,
                    headers=self.config.headers,
                    verify=self.config.verify_ssl
                )
                if response.status_code == 200:
                    rate_limit = int(response.headers.get('X-RateLimit-Limit'))
                    rate_remaining = int(response.headers.get('X-RateLimit-Remaining'))
                    rate_reset = int(response.headers.get('X-RateLimit-Reset'))
                    
                    if self.show_rate_limit:
                        self.logger.info(f'rate limit:{rate_limit}')
                        self.logger.info(f'remaining requests:{rate_remaining}')
                        self.logger.info(f'current time:{datetime.fromtimestamp(current_time)}')
                        self.logger.info(f'rate limit reset time:{datetime.fromtimestamp(rate_reset)}')

                    if rate_remaining < 100:
                        sleep_time = rate_reset - current_time
                        extra_buffer = 60 * 10  # extra 10 minutes
                        sleep_time += extra_buffer

                        if sleep_time > 0:
                            self.logger.info(f'Rate limit low: sleeping for {sleep_time:.2f} seconds')
                            time.sleep(sleep_time)
                            self.logger.info('Rate limit reset: continuing...')
                        else:
                            self.logger.debug('Rate limit should have reset: continuing...')
                
                self.last_check_time = current_time
            except Exception as e:
                self.logger.debug(f'Failed to fetch rate limit info: {str(e)}')

    def _make_request(self, url: str) -> requests.Response:
        """Make an HTTP request to GitHub API with error handling"""
        self._check_rate_limit()
        try:
            response = requests.get(
                url=url,
                headers=self.config.headers,
                verify=self.config.verify_ssl
            )
            response.raise_for_status()
            return response
        except RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            raise ProcessingError(f"GitHub API request failed: {str(e)}")

    def get_repo_actions_permissions(self, repo_name: str) -> Dict:
        """Get Actions permissions for a specific repository"""
        url = f"{self.config.base_url}/repos/{self.config.org}/{repo_name}/actions/permissions/access"
        try:
            response = self._make_request(url)
            repo_info = {
                "Name": repo_name,
                "Full Name": f"{self.config.org}/{repo_name}",
                "URL": f"https://github.com/{self.config.org}/{repo_name}",
                "Action access_level": response.json().get("access_level", "unknown")
            }
            return repo_info
        except ProcessingError as e:
            self.logger.error(f"Error processing repository {repo_name}: {str(e)}")
            return {
                "Name": repo_name,
                "Full Name": f"{self.config.org}/{repo_name}",
                "URL": f"https://github.com/{self.config.org}/{repo_name}",
                "Action access_level": "error"
            }

def read_repo_list(input_file: Optional[Path]) -> List[str]:
    """Read repository list from file if provided"""
    if input_file:
        with open(input_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []

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
        description='Check GitHub Actions permissions for repositories.'
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '-i', '--input-file',
        help='Input file containing repository names (one per line)',
        type=Path
    )
    input_group.add_argument(
        'repos',
        help='Repository names',
        nargs='*',
        default=[]
    )

    parser.add_argument(
        '-o', '--output-file',
        help='Output CSV file path',
        type=Path,
        required=False
    )

    parser.add_argument(
        '--stdout',
        help='Print results to stdout immediately',
        action='store_true'
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
        '--show-rate-limit',
        help='Show GitHub API rate limit information',
        action='store_true'
    )

    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    if not args.stdout and not args.output_file:
        logger.error("At least one output method must be specified: --stdout and/or --output-file")
        sys.exit(1)

    # Validate environment variables
    token = os.getenv('GITHUB_TOKEN')
    org = os.getenv('GITHUB_ORG')

    if not token or not org:
        logger.error("GITHUB_TOKEN and GITHUB_ORG environment variables must be set")
        sys.exit(1)

    # Get repository list
    repos = read_repo_list(args.input_file) if args.input_file else args.repos

    if not repos:
        logger.error("No repositories specified")
        sys.exit(1)

    # Initialize GitHub checker
    config = GitHubConfig(token=token, org=org, verify_ssl=False)
    checker = GitHubActionsChecker(config, show_rate_limit=args.show_rate_limit)

    # Setup CSV writer for stdout if needed
    csv_writer = None
    if args.stdout:
        csv_writer = csv.DictWriter(sys.stdout, fieldnames=['Name', 'Full Name', 'URL', 'Action access_level'])
        csv_writer.writeheader()

    # Process repositories
    results = []
    for repo in repos:
        logger.debug(f"Checking repository: {repo}")
        result = checker.get_repo_actions_permissions(repo)
        
        if args.stdout:
            csv_writer.writerow(result)
            sys.stdout.flush()
        
        if args.output_file:
            results.append(result)

    # Create DataFrame and save to CSV if output file specified
    if args:
        df = pd.DataFrame(results)
        df.to_csv(args.output_file, index=False)
        logger.debug(f"Results written to {args.output_file}")

if __name__ == "__main__":
    main()