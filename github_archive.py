
import requests
import json
import os
import sys
import argparse
import logging
from collections import OrderedDict

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ----------------------------------------------------------------------------------------------------------------------

# get token and org from env variables
str_github_token = os.getenv('GITHUB_TOKEN')
str_github_org = os.getenv('GITHUB_ORG')
str_github_org_archive = os.getenv('GITHUB_ORG_ARCHIVE')

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

def archive_then_move (str_repo_name:str, str_req_num:str) -> (bool):
    if not str_repo_name:
        return False
    #/if

    dict_repo = _get_repo(str_repo_name)
    if not dict_repo:
        logger.error(f'failed to locate repo "{str_repo_name}"')
        return False
    # /fi

    # refresh for proper cases
    str_repo_name = dict_repo['name']
    logger.debug(f'str_repo_name:"{str_repo_name}"')

    if dict_repo['archived']:
        logger.debug(f'repo "{str_repo_name}" is already archived')
    else:
        dict_result = _archive_repo(str_repo_name)
        if not dict_result:
            return False
        # /if
    # /if

    dict_result = _move_repo(str_repo_name)
    if not dict_result:
        return False
    # /if

    bool_result = _update_repo_req_name(str_repo_name, str_req_num)
    if not bool_result:
        return False
    # /if
    return True
# /def

def _archive_repo(str_repo_name: str) -> (dict):
    dict_params = dict_global_params.copy()

    str_rest_url = f'https://api.github.com/repos/{str_github_org}/{str_repo_name}'
    logger.debug(f'action="patch",rest_url="{str_rest_url}"')

    res = requests.patch(str_rest_url,
                       verify=bool_ssl_verify,
                       headers=dict_global_headers,
                       params=dict_params,
                       json={ 'archived':'true' })
    logger.debug(f'res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return {}
    # /fi

    dict_result = json.loads(res.text)

    if res.status_code == 200 and dict_result['archived']:
        logger.debug(f'successfully archive repo "{str_repo_name}"')
    else:
        logger.error(f'failed to archive repo "{str_repo_name}"')
        return {}
    # /else
    return dict_result
# /def

def _move_repo(str_repo_name: str) -> (dict):
    dict_params = dict_global_params.copy()

    str_rest_url = f'https://api.github.com/repos/{str_github_org}/{str_repo_name}/transfer'
    logger.debug(f'action="post",rest_url="{str_rest_url}"')

    res = requests.post(str_rest_url,
                         verify=bool_ssl_verify,
                         headers=dict_global_headers,
                         params=dict_params,
                         json={ 'new_owner':str_github_org_archive })
    logger.debug(f'res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return {}
    # /fi

    dict_result = json.loads(res.text)

    if res.status_code == 422:
        list_errors = dict_result.get('errors',[])
        for dict_item in list_errors:
            str_error_message = dict_item.get('message', '')
            if str_error_message:
                logger.debug(f'str_error_message="{str_error_message}"')
            # /if
        # /for
        return {}
    # /if

    if res.status_code == 202:
        logger.info(f'OK:successfully moved repo "{str_repo_name}" to org "{str_github_org_archive}"')
    else:
        logger.error(f'failed to move repo "{str_repo_name}" to org "{str_github_org_archive}"')
        return {}
    # /else

    return dict_result
# /def

def _update_repo_req_name(str_repo_name:str, str_req_name:str) -> (bool):
    dict_params = dict_global_params.copy()

    str_rest_url = f'https://api.github.com/repos/{str_github_org_archive}/{str_repo_name}/properties/values'
    logger.debug(f'action="patch",rest_url="{str_rest_url}"')

    dict_body = { 'properties': [ { 'property_name' : 'request-num', 'value': str_req_name }] }
    str_body_json = json.dumps(dict_body)

    res = requests.patch(str_rest_url,
                         verify=bool_ssl_verify,
                         headers=dict_global_headers,
                         params=dict_params,
                         data=str_body_json,
                         )
    logger.debug(f'res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return False
    # /fi

    # dict_result = json.loads(res.text)

    if res.status_code == 204:
        logger.debug(f'successfully updated "request-num" property in repo "{str_repo_name}"')
    else:
        logger.error(f'failed to update "request-num" property in repo "{str_repo_name}"')
        return False
    # /else
    return True
# /def

def _get_repo(str_repo_name: str) -> (dict):
    dict_params = dict_global_params.copy()

    str_rest_url = f'https://api.github.com/repos/{str_github_org}/{str_repo_name}'
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

    dict_repo = json.loads(res.text)
    if res.status_code == 200:
        logger.debug(f'successfully retrieved repo "{str_repo_name}"')
    else:
        logger.debug(f'failed to retrieve repo "{str_repo_name}"')
        return {}
    # /else
    return dict_repo
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
        dest='input_file'
    )

    parser.add_argument(
        '-o', '--output-result',
        help='Result of the run in CSV format.',
        dest='output_file'
    )

    parser.add_argument(
        '-r', '--req-num',
        help='Update the custom properties: req-num.',
        dest='req_num',
        default='N/A',
    )

    parser.add_argument('repo_name', nargs='?', default='')

    args = parser.parse_args()
    return parser, args
# /def

def _get_updated_repo_name(str_repo_name) -> str:
    dict_repo = _get_repo(str_repo_name)
    if dict_repo:
        return dict_repo['name']
    # /if
    return str_repo_name
#/if

def _process_input_file(str_input_file: str) -> OrderedDict:
    if not str_input_file:
        return {}
    # /if

    ordereddict_queue = OrderedDict()
    logger.debug(f'input_file:"{str_input_file}"')

    with open(str_input_file, 'r') as f:
        list_lines = f.read().splitlines()
        logger.debug(f'list_lines="{list_lines}"')
        for str_line in list_lines:
            if str_line.isupper():
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
    str_repo_name = args.repo_name
    str_input_file = args.input_file
    str_output_file = args.output_file
    str_req_num = args.req_num

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

    if not str_github_org_archive:
        logger.error('environment variable "GITHUB_ORG_ARCHIVE" is not set or empty.')
        sys.exit(1)
    # /if

    if (not str_repo_name) and (not str_input_file):
        parser.print_help()
    # /if

    logger.debug(f'github_org:"{str_github_org}"')
    logger.debug(f'github_org_archive:"{str_github_org_archive}"')

    if str_output_file:
        logger.debug(f'output_file:"{str_output_file}"')
    # /if

    if str_req_num:
        logger.debug(f'req_num:"{str_req_num}"')
    # /if

    ordereddict_queue = OrderedDict()
    if str_input_file:
        ordereddict_queue = _process_input_file(str_input_file)
    else:
        ordereddict_queue[str_repo_name] = str_req_num
    # /if

    logger.debug(f'ordereddict_queue="{ordereddict_queue}"')

    ordereddict_output_file = OrderedDict()
    for queue in ordereddict_queue:
        logger.debug(f'queue_name:"{queue}"')
        bool_run_result = archive_then_move(queue, str_req_num)
        queue = _get_updated_repo_name(queue)
        ordereddict_output_file[queue] = bool_run_result
    # /for

    if str_output_file:
        logger.debug(f'{ordereddict_output_file}')
        with open(str_output_file, 'w') as f:
            f.write('REPO_NAME,RUN_OK\n')
            for k in ordereddict_output_file:
                f.writelines(f'{k},{ordereddict_output_file[k]}\n')
            # /for
        # /with
    #/if

# /if
