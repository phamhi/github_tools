
import requests
import json
import time
import os
import argparse
import logging
import sys

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

# Get all repositories for the specified organization.
def get_securitychampion_parent_teams() -> (list):
    page = 1
    list_teams = []

    while True:
        list_returned_repos = _get_teams_per_page(page)

        if len(list_returned_repos) == 0:
            break
        # /if

        list_teams.extend(list_returned_repos)
        logger.debug(f'total number of records={len(list_teams)}')

        page += 1
        time.sleep(int_sleep)
    # / while

    list_team_names = [n['name'] for n in list_teams if n['name']]
    list_required_child_teams = ['Admin', 'User']

    list_proper_team_names = []
    for str_team_name in list_team_names:
        bool_result = _is_proper_parent_team(str_team_name, list_required_child_teams)
        if not bool_result:
            continue
        # /if
        list_proper_team_names.append(str_team_name)
    # /for

    return list_proper_team_names
# /def

def _is_proper_parent_team(str_team_name: str, list_child_prefixes: list) -> (bool):
    list_child_teams = _get_child_teams(str_team_name)

    if not list_child_teams:
        logger.debug(f'failed to find child teams for "{str_team_name}"')
        return False
    # /if

    set_required_child_prefixes = set(list_child_prefixes)
    set_src_child_prefixes = set()

    for dict_child in list_child_teams:
        str_child_name = dict_child['name']
        logger.debug(f'found child:{str_child_name}')
        str_child_name_postfix = str_child_name.split('_')[-1]
        set_src_child_prefixes.add(str_child_name_postfix)
    # /for
    logger.debug(f'set_required_child_prefixes="{set_required_child_prefixes}"')
    logger.debug(f'set_src_child_prefixes="{set_src_child_prefixes}"')

    for str_required_child in set_required_child_prefixes:
        if str_required_child not in set_src_child_prefixes:
            logger.debug(f'failed to locate the required child team "{str_required_child}" in the parent team "{str_team_name}"')
            return False
        # /if
    # /for

    return True
# /def

def _get_child_teams(str_team_name: str) -> (dict):
    dict_params = dict_global_params.copy()

    str_rest_url = f'https://api.github.com/orgs/{str_github_org}/teams/{str_team_name}/teams'
    # logger.debug(f'action="get",rest_url="{str_rest_url}"')

    res = requests.get(str_rest_url,
                       verify=bool_ssl_verify,
                       headers=dict_global_headers,
                       params=dict_params)
    logger.debug(f'res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return {}
    # /fi

    list_child_teams = json.loads(res.text)
    if res.status_code == 200:
        logger.debug(f'successfully retrieved child teams for "{str_team_name}"')
    else:
        logger.debug(f'failed to retrieve child teams for "{str_team_name}"')
        return {}
    # /else
    return list_child_teams
# /def

# Get repositories for the specified organization on specific page
# https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-organization-repositories
def _get_teams_per_page(page: int, per_page=100) -> (list):
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

# ----------------------------------------------------------------------------------------------------------------------

def parse_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Get SecurityChampion "parent"-type Teams.'
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

def create_logger() -> logging.Logger:
    common_formatter = logging.Formatter('%(funcName)s:%(levelname)s:%(message)s')
    logger = logging.getLogger(__name__)

    # set console logging
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(common_formatter)
    logger.addHandler(c_handler)

    return logger
# /def

# ----------------------------------------------------------------------------------------------------------------------

logger = create_logger()

if __name__ == '__main__':
    # parse arguments passed
    args = parse_args()
    #
    int_verbosity = args.verbosity

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

    list_team_names =  get_securitychampion_parent_teams()
    logger.debug(f'got a total of {len(list_team_names)} team(s)')

    if not len(list_team_names):
        exit(1)
    # /if

    for i in list_team_names:
        print(i)
    # /for
# # /if
