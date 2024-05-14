import argparse
import logging
import os
import sys

str_postfix = 'SecurityChampion'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate Github maintainers input list.'
    )
    parser.add_argument(
        '--debug',
        help='Display "debugging" in output (defaults to "info").',
        action='store_const', dest='verbosity',
        const=logging.DEBUG, default=logging.INFO,
    )
    parser.add_argument('input_list')
    args = parser.parse_args()

    str_input_list = args.input_list
    int_verbosity = args.verbosity

    logger = logging.getLogger(__name__)
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(logging.Formatter('%(funcName)s:%(levelname)s:%(message)s'))
    logger.addHandler(c_handler)
    logger.setLevel(int_verbosity)

    logger.debug(f'str_input_list="{str_input_list}"')

    if not os.path.isfile(str_input_list):
        logger.error(f'input file "{str_input_list}" cannot be found')
        sys.exit(1)
    # /if

    with open(str_input_list, 'r') as f:
        list_lines = f.read().splitlines()
    # /with

    print(f'SOURCE_TEAM,DESTINATION_TEAM')
    for str_line in list_lines:
        print(f'{str_line},{str_line}_{str_postfix}')
    # /for
#/if