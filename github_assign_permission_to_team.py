import requests
import json
import os
import sys
import argparse
import logging
import time

from collections import OrderedDict
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ----------------------------------------------------------------------------------------------------------------------

# get token and org from env variables
str_github_token = os.getenv('GITHUB_TOKEN')
str_github_org = os.getenv('GITHUB_ORG')

# str_default_github_org = 'myorg' # default Github Org

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
    # sort='full_name',
)

# ----------------------------------------------------------------------------------------------------------------------

def assign_permission(str_team_name:str, str_permission:str, str_repo:str) -> bool:
    dict_params = dict_global_params.copy()

    dict_body = dict()
    dict_body['permission'] = str_permission
    str_body_json = json.dumps(dict_body)

    str_rest_url = f'https://api.github.com/orgs/{str_github_org}/teams/{str_team_name}/repos/{str_github_org}/{str_repo}'
    logger.debug(f'action="put",rest_url="{str_rest_url}"')
    logger.debug(f'body="{dict_body}"')

    _handle_github_rate_limit()
    res = requests.put(str_rest_url,
                       verify=bool_ssl_verify,
                       headers=dict_global_headers,
                       params=dict_params,
                       data=str_body_json)
    logger.debug(f'res.status_code = {res.status_code}')

    if res.status_code == 401:
        logger.error(f'credential rejected')
        return False
    # /if

    if res.status_code == 204:
        return True
    # /if

    logger.error(f'{res.text}')
    return False
# /def

# ----------------------------------------------------------------------------------------------------------------------

def _handle_github_rate_limit():
    dict_params = dict_global_params.copy()

    str_rest_url = "https://api.github.com/rate_limit"
    res = requests.get(str_rest_url,
                       verify=bool_ssl_verify,
                       headers=dict_global_headers,
                       params=dict_params)

    # get current ime
    float_current_time = time.time()

    int_rate_limit = int(res.headers.get('X-RateLimit-Limit'))
    int_rate_remaining = int(res.headers.get('X-RateLimit-Remaining'))
    int_rate_reset = int(res.headers.get('X-RateLimit-Reset'))

    if res.status_code == 200:
        if int_rate_remaining < 100:
            logger.debug(f'rate limit:{int_rate_limit}')
            logger.debug(f'remaining requests:{int_rate_remaining}')
            logger.debug(f'current time:{datetime.fromtimestamp(float_current_time)}')
            logger.debug(f'rate limit reset time:{datetime.fromtimestamp(int_rate_reset)}')

            float_sleep_time = int_rate_reset - time.time()
            extra_buffer = 60 * 10 # extra 10 minutes
            float_sleep_time += extra_buffer

            if float_sleep_time > 0:
                logger.debug(f'rate limit hit:sleeping for {float_sleep_time:.2f} seconds.')
                time.sleep(float_sleep_time)
                logger.debug(f'rate limit reset:continuing...')
            # /fi
            else:
                logger.debug(f'rate limit should have reset:continuing...')
            # /else
        # /if
    # /if
    else:
        logger.debug(f'failed to fetch rate limit info:status code: {res.status_code}')
    # /else
    logger.debug(f'rate limit has not been reached:remaining requests:{int_rate_remaining}')
# /def

def create_logger(str_basename:str) -> logging.Logger:
    str_basename = os.path.basename(str_basename)
    str_datetime_now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    # str_log_name = f'{str_basename}.{str_datetime_now}.log'

    common_formatter = logging.Formatter('%(funcName)s:%(levelname)s:%(message)s')
    logger = logging.getLogger(__name__)

    # set console logging
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(common_formatter)
    logger.addHandler(c_handler)

    # f_handler = logging.FileHandler(str_log_name)
    # f_handler.setFormatter(common_formatter)
    # logger.addHandler(f_handler)

    # logger.debug(f'str_log_name:"{str_log_name}"')
    return logger
# /def

def parse_args() :
    parser = argparse.ArgumentParser(
        description='Assign permission to a Github Team.'
    )

    parser.add_argument(
        '--debug',
        help='display "debugging" in output (defaults to "info").',
        action='store_const', dest='verbosity',
        const=logging.DEBUG, default=logging.INFO,
    )

    parser.add_argument(
        '--error-only',
        help='display "error" in output only (filters "info").',
        action='store_const', dest='verbosity',
        const=logging.ERROR,
    )

    parser.add_argument(
        '-p', '--permission',
        help='Permission to use.',
        dest='permission'
    )

    parser.add_argument(
        '-r', '--repo',
        help='Repository to be updated.',
        dest='repo'
    )

    parser.add_argument('team_name', nargs='?', default='')

    args = parser.parse_args()
    return parser, args
# /def

# ----------------------------------------------------------------------------------------------------------------------

logger = create_logger(sys.argv[0])

if __name__ == '__main__':
    # parse arguments passed
    parser, args = parse_args()
    #
    int_verbosity = args.verbosity
    str_team_name = args.team_name
    str_permission = args.permission
    str_repo = args.repo

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

    if not str_team_name or not str_permission or not str_repo:
        parser.print_help()
    # /if

    logger.debug(f'str_team_name:"{str_team_name}"')
    logger.debug(f'str_permission:"{str_permission}"')
    logger.debug(f'str_repo:"{str_repo}"')

    if not assign_permission(str_team_name, str_permission, str_repo):
        sys.exit(1)
    # /if
# /if