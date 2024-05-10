
import requests
import json
import os
import sys
import argparse
import logging

import pprint
from collections import OrderedDict
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ----------------------------------------------------------------------------------------------------------------------

# get token and org from env variables
str_github_token = os.getenv('GITHUB_TOKEN')
str_github_org = os.getenv('GITHUB_ORG')

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

def copy_maintainers(str_source_team, str_destination_team) -> (bool):
    if not str_source_team or not str_destination_team:
        return False
    # /if

    dict_source_team = _get_team(str_source_team)
    if not dict_source_team:
        logger.error(f'failed to locate the source team "{str_source_team}"')
        return False
    # /fi

    dict_destination_team = _get_team(str_destination_team)
    if not dict_destination_team:
        logger.error(f'failed to locate the destination team "{str_source_team}"')
        return False
    # /fi

    # refresh for proper cases
    str_source_team = dict_source_team['name']
    logger.debug(f'str_source_team:"{str_source_team}"')
    str_destination_team = dict_destination_team['name']
    logger.debug(f'str_destination_team:"{str_destination_team}"')

    list_maintainers = _get_maintainer(str_source_team)
    logger.debug(f'list_maintainers={[i["login"] for i in list_maintainers]}')

    for dict_user in list_maintainers:
        dict_result = _set_maintainer(str_destination_team, dict_user['login'])
    # /for

    logger.info(f'OK:sucessfully added maintainers to team "{str_destination_team}"')
    return True
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

    dict_result = json.loads(res.text)
    if res.status_code == 200:
        logger.debug(f'successfully retrieved team "{str_team_name}"')
    else:
        logger.debug(f'failed to retrieve team "{str_team_name}"')
        logger.debug(dict_result)
        return {}
    # /else
    return dict_result
# /def

def _get_maintainer(str_team_name: str) -> (list):
    dict_params = dict_global_params.copy()
    dict_params['role'] = 'maintainer'

    str_rest_url = f'https://api.github.com/orgs/{str_github_org}/teams/{str_team_name}/members'
    logger.debug(f'action="get",rest_url="{str_rest_url}"')

    res = requests.get(str_rest_url,
                       verify=bool_ssl_verify,
                       headers=dict_global_headers,
                       params=dict_params)
    logger.debug(f'res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return []
    # /fi

    list_result = json.loads(res.text)
    if res.status_code == 200:
        logger.debug(f'successfully retrieved maintainers "{str_team_name}"')
    else:
        logger.debug(f'failed to retrieve maintainers "{str_team_name}"')
        logger.debug(list_result)
        return []
    # /else
    return list_result
# /def

def _set_maintainer(str_team_name:str, str_login:list) -> (dict):
    dict_params = dict_global_params.copy()
    dict_params['role'] = 'maintainer'

    str_rest_url = f'https://api.github.com/orgs/{str_github_org}/teams/{str_team_name}/memberships/{str_login}'
    logger.debug(f'action="put",rest_url="{str_rest_url}"')

    res = requests.put(str_rest_url,
                       verify=bool_ssl_verify,
                       headers=dict_global_headers,
                       params=dict_params,
                       json={ 'role':'maintainer' })
    logger.debug(f'res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return {}
    # /fi

    dict_result = json.loads(res.text)
    if res.status_code == 200:
        logger.debug(f'successfully gave maintainer role to "{str_login}" in team "{str_team_name}')
    else:
        logger.debug(f'failed to give maintainer role to "{str_login}" in team "{str_team_name}')
        logger.debug(dict_result)
        return {}
    # /else
    return dict_result
# /def

# ----------------------------------------------------------------------------------------------------------------------

def parse_args() :
    parser = argparse.ArgumentParser(
        description='Archive Github repo(s).'
    )

    parser.add_argument(
        '--debug',
        help='Display "debugging" in output (defaults to "info").',
        action='store_const', dest='verbosity',
        const=logging.DEBUG, default=logging.INFO,
    )

    parser.add_argument(
        '--error-only',
        help='Display "error" in output only (filters "info").',
        action='store_const', dest='verbosity',
        const=logging.ERROR,
    )

    parser.add_argument(
        '-i', '--input-file',
        help='File contains list of repos to be processed.',
        dest='input_file',
        default='',
    )

    parser.add_argument(
        '-o', '--output-result',
        help='Result of the run in CSV format.',
        dest='output_file'
    )

    parser.add_argument(
        '-s', '--source-team',
        help='Copy maintainers from this source team.',
        dest='source_team',
        default='',
    )

    parser.add_argument(
        '-d', '--destination-team',
        help='Copy maintainers to this destination team',
        dest='destination_team',
        default='',
    )

    # parser.add_argument('repo_name', nargs='?', default='')

    args = parser.parse_args()
    return parser, args
# /def


def _get_first_char(s:str) -> str:
    return s[0] if s else ''
# /def

def _process_input_file(str_input_file: str) -> OrderedDict:
    if not str_input_file:
        return OrderedDict()
    # /if

    ordereddict_queue = OrderedDict()
    logger.debug(f'input_file:"{str_input_file}"')

    with open(str_input_file, 'r') as f:
        list_lines = f.read().splitlines()
        logger.debug(f'list_lines="{list_lines}"')
        for str_line in list_lines:
            # skip header line (assuming all uppercase)
            if str_line.isupper():
                continue
            # /if

            # skip if first non-space character is a '#' character
            if _get_first_char(str_line) == '#':
                continue
            # /if

            list_split = str_line.split(',')
            if len(list_split)<2:
                list_split.append('')
            # /if
            logger.debug(f'list_split="{list_split}"')
            ordereddict_queue[list_split[0]] = list_split[1]
        # /for
    # /with
    return ordereddict_queue
# /def

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # parse arguments passed
    parser, args = parse_args()

    int_verbosity = args.verbosity
    #
    str_input_file = args.input_file
    str_output_file = args.output_file
    #
    str_source_team = args.source_team
    str_destination_team = args.destination_team

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

    # if (not str_repo_name) and (not str_input_file):
    #     parser.print_help()
    # # /if

    logger.debug(f'github_org:"{str_github_org}"')

    logger.debug(f'source_team:"{str_source_team}"')
    logger.debug(f'destination_team:"{str_destination_team}"')

    logger.debug(f'input_file:"{str_input_file}"')
    logger.debug(f'output_file:"{str_output_file}"')

    # if str_input_file is not set..
    # str_source_team and str_destination_team need to be set
    if not str_input_file and (not str_source_team or not str_destination_team):
        parser.print_help()
        sys.exit(1)
    # /if

    ordereddict_queue = OrderedDict()
    if str_input_file:
        ordereddict_queue = _process_input_file(str_input_file)
    else:
        ordereddict_queue[str_source_team] = str_destination_team
    # /if

    logger.debug(f'ordereddict_queue="{ordereddict_queue}"')

    ordereddict_output_file = OrderedDict()
    for str_loop_source in ordereddict_queue:
        str_loop_destination = ordereddict_queue[str_loop_source]

        if not str_loop_source or not str_loop_destination:
            logger.debug(f'skipping teams: "{str_loop_source}" and "{str_loop_destination}"')
            continue
        # /if

        logger.debug(f'str_loop_source="{str_loop_source}"')
        logger.debug(f'str_loop_destination="{str_loop_destination}"')

        bool_run_result = copy_maintainers(str_loop_source, str_loop_destination)
        # queue = _get_updated_repo_name(queue)

        ordereddict_output_file[str_loop_source] = {'destination_team': str_loop_destination,
                                                    'run_ok':bool_run_result}
    # /for

    if str_output_file:
        logger.debug(f'{ordereddict_output_file}')
        with open(str_output_file, 'w') as f:
            f.write('SOURCE_TEAM,DESTINATION_TEAM,RUN_OK\n')
            for str_loop_source in ordereddict_output_file:
                str_loop_destination = ordereddict_output_file[str_loop_source]['destination_team']
                bool_result = ordereddict_output_file[str_loop_source]['run_ok']
                f.writelines(f'{str_loop_source},{str_loop_destination},{bool_result}\n')
            # /for
        # /with
    #/if

# /if
