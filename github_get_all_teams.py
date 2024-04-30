
import requests
import json
import time
import os
import sys
import argparse
import logging

from pprint import pprint
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ----------------------------------------------------------------------------------------------------------------------

# get token and org from env variables
str_github_token = os.getenv('GITHUB_TOKEN')
str_github_org = os.getenv('GITHUB_ORG')

int_sleep = 0
bool_ssl_verify = False

dict_global_headers = {
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'Authorization': f'Bearer {str_github_token}',
}

# default sort to full_name
dict_global_params = dict(
    sort='full_name',
)

# ----------------------------------------------------------------------------------------------------------------------

# Get repositories for the specified organization on specific page
# https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-organization-repositories
def get_teams_per_page(page: int, per_page=100) -> (list):
    dict_params = dict_global_params.copy()
    dict_params['per_page'] = per_page
    dict_params['page'] = page

    res = requests.get(f'https://api.github.com/orgs/{str_github_org}/teams',
                       verify=bool_ssl_verify,
                       headers=dict_global_headers,
                       params=dict_params)
    logger.debug(f'page={page},res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return []
    # /fi

    if res.status_code == 403:
        logger.error(f'unauthorized access to "{str_github_org}"')
        logger.error(f'{res.text}')
        return []
    # /fi

    if res.status_code != 200:
        logger.debug(f'page={page},no more data')
        return []
    # /fi

    list_data = json.loads(res.text)
    logger.debug(f'number of records returned={len(list_data)}')
    return list_data
# /def

# Get all repositories for the specified organization.
def get_all_teams() -> (list):
    page = 1
    list_all_repos = []

    while True:
        list_returned_repos = get_teams_per_page(page)

        if len(list_returned_repos) == 0:
            break
        # /if

        list_all_repos.extend(list_returned_repos)
        logger.debug(f'total number of records={len(list_all_repos)}')

        page += 1
        time.sleep(int_sleep)
    # / while

    return list_all_repos
# /def

# ----------------------------------------------------------------------------------------------------------------------

def parse_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Get all Github teams and output in Python format'
    )

    parser.add_argument(
        '--debug',
        help='Display "debugging" in output (defaults to "info")',
        action='store_const', dest='verbosity',
        const=logging.DEBUG, default=logging.INFO,
    )

    parser.add_argument(
        '--error-only',
        help='Display "error" in output only (filters "info")',
        action='store_const', dest='verbosity',
        const=logging.ERROR,
    )

    args = parser.parse_args()
    return args
# /def

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # parse arguments passed
    args = parse_args()

    int_verbosity = args.verbosity

    logger = logging.getLogger(__name__)
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(logging.Formatter('%(funcName)s:%(levelname)s:%(message)s'))
    logger.addHandler(c_handler)

    # set logging verbosity
    logger.setLevel(int_verbosity)

    logger.debug(f'verbosity "level":"{logging.getLevelName(int_verbosity)}"')

    if not str_github_token:
        logger.error('environment variable "GITHUB_TOKEN" is not set or empty.')
        sys.exit(1)
    # /if

    if not str_github_org:
        logger.error('environment variable "GITHUB_ORG" is not set or empty.')
        sys.exit(1)
    # /if

    logger.debug(f'github org:"{str_github_org}"')

    list_teams =  get_all_teams()
    logger.debug(f'got a total of {len(list_teams)} team(s)')

    pprint(list_teams)
    if not len(list_teams):
        exit(1)
    # /if

# # /if
