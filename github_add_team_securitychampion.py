
import requests
import json
import time
import os
import sys
import argparse
import logging

from urllib3.exceptions import InsecureRequestWarning
from pprint import pformat
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ----------------------------------------------------------------------------------------------------------------------

# get token and org from env variables
str_github_token = os.getenv('GITHUB_TOKEN')
str_github_org = os.getenv('GITHUB_ORG')

# str_default_github_org = 'myorg' # default Github Org
# str_default_output_file = 'output.json'

str_default_team_security_postfix_name = 'SecurityChampion'

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

def add_security_team(str_team_parent_name:str, str_team_security_postfix_name:str) -> (bool):
    str_team_security_name = f'{str_team_parent_name}_{str_team_security_postfix_name}'
    logger.debug(f'str_security_team_name:"{str_team_security_name}"')

    dict_team_parent = _get_team(str_team_parent_name)
    if not dict_team_parent:
        logger.info(f'failed to locate team "{str_team_parent_name}"')
        return False
    # /fi

    int_team_parent_id = dict_team_parent.setdefault('id', 0)

    if not _is_proper_parent_team(str_team_parent_name, ['Admin', 'User']):
        return False
    # /if

    # check if security team already exists
    dict_team_security = _get_team(str_team_security_name)
    if dict_team_security:
        logger.info(f'security team "{str_team_security_name}" already exists inside parent team "{str_team_parent_name}"')
        return True
    else:
        _add_child_team(str_team_security_name, int_team_parent_id)
    # /if


# /def

def _is_proper_parent_team(str_team_name: str, list_child_prefixes: list) -> (bool):
    list_child_teams = _get_child_teams(str_team_name)

    if not list_child_teams:
        logger.info(f'failed to find child teams for "{str_team_name}"')
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
            logger.info(f'failed to locate the required child team "{str_required_child}" in the parent team "{str_team_name}"')
            return False
        # /if
    # /for

    return True
# /def

def _get_child_teams(str_team_name: str) -> (dict):
    dict_params = dict_global_params.copy()

    str_rest_url = f'https://api.github.com/orgs/{str_github_org}/teams/{str_team_name}/teams'
    logger.debug(f'action="get",rest_url="{str_rest_url}"')

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

def _get_team(str_team_name: str) -> (dict):
    dict_params = dict_global_params.copy()

    str_rest_url = f'https://api.github.com/orgs/{str_github_org}/teams/{str_team_name}'
    logger.debug(f'action="get",rest_url="{str_rest_url}"')

    res = requests.get(str_rest_url,
                       verify=bool_ssl_verify,
                       headers=dict_global_headers,
                       params=dict_params)
    logger.debug(f'res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return {}
    # /fi

    dict_team = json.loads(res.text)
    if res.status_code == 200:
        logger.debug(f'successfully retrieved team "{str_team_name}"')
    else:
        logger.debug(f'failed to retrieve team "{str_team_name}"')
        return {}
    # /else
    return dict_team
# /def


def _add_child_team(str_team_name:str, int_team_parent_id:int) -> (dict):
    dict_params = dict_global_params.copy()

    dict_body = dict()
    dict_body['name'] = str_team_name
    dict_body['privacy'] = 'closed'
    dict_body['parent_team_id'] = int_team_parent_id

    str_body_json = json.dumps(dict_body)

    str_rest_url = f'https://api.github.com/orgs/{str_github_org}/teams'
    logger.debug(f'action="post",rest_url="{str_rest_url}"')
    logger.debug(f'body="{dict_body}"')

    res = requests.post(str_rest_url,
                       verify=bool_ssl_verify,
                       headers=dict_global_headers,
                       params=dict_params,
                       data=str_body_json)
    logger.debug(f'res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return {}
    # /fi

    if res.status_code == 201:
        logger.info(f'security team "{str_team_name}" created successfully')
    else:
        logger.error(f'failed to create team "{str_team_name}"')
        logger.error(f'{res.text}')
        return {}
    # /else

    dict_new_team = json.loads(res.text)
    # logger.debug(f'{pformat((dict_new_team))}')
    return dict_new_team
# /def

def remove_duplicates(list_input:list) -> (list):
    from collections import OrderedDict
    return list(OrderedDict.fromkeys(list_input))
# /def

# ----------------------------------------------------------------------------------------------------------------------

def parse_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Create the SecurityChampion Github Team.'
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

    parser.add_argument('team_parent_name', nargs='+')

    args = parser.parse_args()
    return args
# /def

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # parse arguments passed
    args = parse_args()

    int_verbosity = args.verbosity
    list_team_parent_name = remove_duplicates(args.team_parent_name)

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

    logger.debug(f'github_org:"{str_github_org}"')
    logger.debug(f'team_parent_name:"{list_team_parent_name}"')

    for str_team_parent_name in list_team_parent_name:
        add_security_team(str_team_parent_name, str_default_team_security_postfix_name)
    # /for
# /if
