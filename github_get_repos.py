#!/usr/bin/env python3

"""
GitHub Repository Lister
-----------------------
Lists all repositories in a GitHub organization with their key properties.
Exports data to Excel or CSV format.

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
from requests.exceptions import RequestException
import pandas as pd
from urllib3.exceptions import InsecureRequestWarning

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

class GitHubRepoLister:
    """Lists GitHub repositories with pagination support"""
    
    def __init__(self, config: GitHubConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def _make_request(self, url: str, params: Optional[Dict] = None) -> requests.Response:
        """Make an HTTP request to GitHub API with error handling"""
        try:
            response = requests.get(
                url=url,
                headers=self.config.headers,
                params=params,
                verify=self.config.verify_ssl
            )
            response.raise_for_status()
            return response
        except RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            raise ProcessingError(f"GitHub API request failed: {str(e)}")

    def get_all_repos(self, per_page: int = 100) -> List[Dict]:
        """Get all repositories from the organization"""
        url = f"{self.config.base_url}/orgs/{self.config.org}/repos"
        repos = []
        page = 1
        
        while True:
            self.logger.debug(f"Fetching page {page}")
            params = {
                "per_page": per_page,
                "page": page,
                "sort": "full_name",
                "direction": "asc"
            }
            
            try:
                response = self._make_request(url, params)
                page_repos = response.json()
                
                if not page_repos:
                    break
                    
                repos.extend(page_repos)
                page += 1
                
            except ProcessingError:
                break
                
        return repos

def get_repo_dataframe(repos: List[Dict]) -> pd.DataFrame:
    """Convert repository data to DataFrame"""
    data = []
    for repo in repos:
        repo_data = {
            'Name': repo.get('name', ''),
            'Full Name': repo.get('full_name', ''),
            'URL': repo.get('html_url', ''),
            'Description': repo.get('description', ''),
            'Private': repo.get('private', False),
            'Archived': repo.get('archived', False),
            'Disabled': repo.get('disabled', False),
            'Created At': repo.get('created_at', ''),
            'Updated At': repo.get('updated_at', ''),
            'Language': repo.get('language', ''),
            'Forks Count': repo.get('forks_count', 0),
            'Stars Count': repo.get('stargazers_count', 0)
        }
        data.append(repo_data)
    return pd.DataFrame(data)

def write_output(repos: List[Dict], output_file: Path, format_type: str) -> None:
    """Write repository data to specified format"""
    try:
        df = get_repo_dataframe(repos)
        
        if format_type == 'excel':
            writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
            df.to_excel(writer, sheet_name='Repositories', index=False)
            
            # Auto-adjust columns width
            worksheet = writer.sheets['Repositories']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                ) + 2
                worksheet.set_column(idx, idx, max_length)
            
            writer.close()
        else:  # csv
            df.to_csv(output_file, index=False)
                
    except Exception as e:
        logging.error(f"Error writing output file: {str(e)}")
        raise

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
        description='List all repositories in a GitHub organization.'
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
        '-o', '--output-file',
        help='Output file path (.xlsx or .csv)',
        type=Path,
        required=True
    )
    
    parser.add_argument(
        '-p', '--pattern',
        help='Regular expression pattern to filter repository names',
        type=str,
        default=None
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
    
    # Validate output file format
    output_format = args.output_file.suffix.lower()
    if output_format not in ['.xlsx', '.csv']:
        logger.error("Output file must be either .xlsx or .csv")
        sys.exit(1)
    
    # Initialize GitHub lister
    config = GitHubConfig(token=token, org=org, verify_ssl=False)
    lister = GitHubRepoLister(config)
    
    try:
        # Get all repositories
        repos = lister.get_all_repos()
        logger.info(f"Found {len(repos)} repositories")
        
        # Filter repositories by pattern if provided
        if args.pattern:
            import re
            pattern = re.compile(args.pattern)
            repos = [repo for repo in repos if pattern.search(repo['name'])]
            logger.info(f"Filtered to {len(repos)} repositories matching pattern: {args.pattern}")
        
        # Write output file
        format_type = 'excel' if output_format == '.xlsx' else 'csv'
        write_output(repos, args.output_file, format_type)
        logger.info(f"Repository data written to {args.output_file}")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()