
import requests
import json
import os
import sys
import argparse
import logging


from collections import OrderedDict
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime


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
    if not str_team_parent_name:
        return False
    #/if

    dict_team_parent = _get_team(str_team_parent_name)
    if not dict_team_parent:
        logger.error(f'failed to locate team "{str_team_parent_name}"')
        return False
    # /fi

    # refresh for proper cases
    str_team_parent_name = dict_team_parent['name']
    str_team_security_name = f'{str_team_parent_name}_{str_team_security_postfix_name}'
    logger.debug(f'str_security_team_name:"{str_team_security_name}"')

    int_team_parent_id = dict_team_parent.setdefault('id', 0)

    # check if security team already exists
    dict_team_security = _get_team(str_team_security_name)
    if dict_team_security:
        logger.info(f'OK:security team "{str_team_security_name}" already exists inside parent team "{str_team_parent_name}"')
        return True
    # /if

    # logger.debug(_get_team_maintainers(str_team_name))

    if not _is_proper_parent_team(str_team_parent_name, ['Admin', 'User']):
        return False
    # /if

    if not _add_child_team(str_team_security_name, int_team_parent_id):
        return False
    #/if
    return True
# /def

def _is_proper_parent_team(str_team_name: str, list_child_prefixes: list) -> (bool):
    list_child_teams = _get_child_teams(str_team_name)

    if not list_child_teams:
        logger.error(f'failed to find child teams for "{str_team_name}"')
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
            logger.error(f'failed to locate the required child team "{str_required_child}" in the parent team "{str_team_name}"')
            return False
        # /if
    # /for

    return True
# /def

def _get_team_maintainers(str_team_name: str) -> (dict):
    dict_params = dict_global_params.copy()
    dict_params['role'] = 'maintainer'

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

    list_maintainers = json.loads(res.text)
    if res.status_code == 200:
        logger.debug(f'successfully retrieved maintainers for "{str_team_name}"')
    else:
        logger.debug(f'failed to retrieve maintainers for "{str_team_name}"')
        return {}
    # /else
    return list_maintainers
# /def

def _get_child_teams(str_team_name: str) -> (list):
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
        logger.info(f'OK:security team "{str_team_name}" created successfully')
    else:
        logger.error(f'FAILED:failed to create team "{str_team_name}"')
        logger.error(f'{res.text}')
        return {}
    # /else

    dict_new_team = json.loads(res.text)
    # logger.debug(f'{pformat((dict_new_team))}')
    return dict_new_team
# /def

def remove_duplicates(list_input:list) -> (list):
    return list(OrderedDict.fromkeys(list_input))
# /def

# ----------------------------------------------------------------------------------------------------------------------

def parse_args() :
    parser = argparse.ArgumentParser(
        description='Create the SecurityChampion Github Team.'
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
        help='File contains list of Teams to be processed.',
        dest='input_file'
    )

    parser.add_argument(
        '-o', '--output-result',
        help='Result of the run in CSV format.',
        dest='output_file'
    )

    parser.add_argument('team_name', nargs='?', default='')

    args = parser.parse_args()
    return parser, args
# /def

def _get_updated_team_name(str_team_name) -> str:
    dict_team = _get_team(str_team_name)
    if dict_team:
        return dict_team['name']
    # /if
    return str_team_name
#/if

def create_logger(str_basename:str) -> logging.Logger:
    str_basename = os.path.basename(str_basename)
    str_datetime_now = datetime.now().strftime("%Y-%m-%d_%T-%f")
    str_log_name = f'{str_basename}.{str_datetime_now}.log'

    common_formatter = logging.Formatter('%(funcName)s:%(levelname)s:%(message)s')
    logger = logging.getLogger(__name__)

    # set console logging
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(common_formatter)
    logger.addHandler(c_handler)

    f_handler = logging.FileHandler(str_log_name)
    f_handler.setFormatter(common_formatter)
    logger.addHandler(f_handler)

    logger.debug(f'str_log_name:"{str_log_name}"')
    return logger
# /def

# ----------------------------------------------------------------------------------------------------------------------

logger = create_logger(sys.argv[0])

if __name__ == '__main__':
    # parse arguments passed
    parser, args = parse_args()
    #
    int_verbosity = args.verbosity
    str_team_name = args.team_name
    str_input_file = args.input_file
    str_output_file = args.output_file

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

    if (not str_team_name) and (not str_input_file):
        parser.print_help()
    # /if

    logger.debug(f'github_org:"{str_github_org}"')

    if str_output_file:
        logger.debug(f'output_file:"{str_output_file}"')
    # /if

    list_queue = []
    if str_input_file:
        logger.debug(f'input_file:"{str_input_file}"')
        with open(str_input_file, 'r') as f:
            list_team_names = f.read().splitlines()
            list_team_names = [i for i in list_team_names if i]
            for str_name in list_team_names:
                list_queue.append(str_name)
            # /for
        # /with
    elif str_team_name:
        list_queue.append(str_team_name)
    # /if

    list_queue = remove_duplicates(list_queue)
    logger.debug(f'list_queue:"{list_queue}"')

    ordereddict_output_file = OrderedDict()

    for str_queue_name in list_queue:
        logger.debug(f'queue_name:"{str_queue_name}"')
        bool_run_result = add_security_team(str_queue_name, str_default_team_security_postfix_name)
        str_queue_name = _get_updated_team_name(str_queue_name)
        ordereddict_output_file[str_queue_name] = bool_run_result
    # /for

    if str_output_file:
        logger.debug(f'{ordereddict_output_file}')
        with open(str_output_file, 'w') as f:
            f.write('TEAM_NAME,RUN_OK\n')
            for k in ordereddict_output_file:
                f.writelines(f'{k},{ordereddict_output_file[k]}\n')
            # /for
        # /with
    #/if

# /if
