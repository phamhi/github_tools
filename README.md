# github_tools

## Example end-to-end testing

Export the required environment variables

```shell
export GITHUB_TOKEN=mytoken
export GITHUB_ORG=myorg
```

Get all Github Teams that are "parent" type (i.e. has at least 1 child team)

```shell
python github_get_teams.py --parent-only > all_parent_teams.txt
```

Create the "SecurityChampion" team from the input list: all_parent_teams.txt
 - Each run will create a log file (e.g. github_add_team_securitychampion.py.2024-05-14_17:59:46-447753.log)
 - the parameter "-o run_securitychamption_result.csv" will create a csv file containing the result of each team

```shell
python github_add_team_securitychampion.py -i all_parent_teams.txt -o run_securitychamption_result.csv
```

An example output of the run_securitychamption_result.csv file (can be easily imported to Excel:

```shell
TEAM_NAME,RUN_OK
Banana,False
Strawberry,False
StarfoxHUB_1010,True
Apple,False
```

Generate an input list of "parent" Teams' Maintainers to be copied to the SecurityChamption Teams

```shell
% python generate_teams_maintainer_list.py all_parent_teams.txt

```
SOURCE_TEAM,DESTINATION_TEAM
Account,Account_SecurityChampion
Admin,Admin_SecurityChampion
Android,Android_SecurityChampion
EPO,EPO_SecurityChampion
Interns,Interns_SecurityChampion
iOS,iOS_SecurityChampion
Mobile,Mobile_SecurityChampion
Platform,Platform_SecurityChampion
Reports,Reports_SecurityChampion
StarfoxHUB_1010,StarfoxHUB_1010_SecurityChampion

## generate_teams_maintainer_list.py

Invoke the help argument

Personal Access Token (PAT) requires the following permissions:
- admin:org: write:org, read:org

Remember to *authorize* in org if SSO is used.

```shell
% python generate_teams_maintainer_list.py --help
usage: generate_teams_maintainer_list.py [-h] [--debug] input_list

Generate Github maintainers input list.

positional arguments:
  input_list

options:
  -h, --help  show this help message and exit
  --debug     Display "debugging" in output (defaults to "info").
```

```shell
% python generate_teams_maintainer_list.py all_parent_teams.txt 
SOURCE_TEAM,DESTINATION_TEAM
StarfoxHUB_1010,StarfoxHUB_1010_SecurityChampion
```

## github_add_team_securitychampion.py

Invoke the help argument

Personal Access Token (PAT) requires the following permissions:
- admin:org: write:org, read:org

Remember to *authorize* in org if SSO is used.

```shell
% python github_add_team_securitychampion.py --help
usage: github_add_team_securitychampion.py [-h] [--debug] [--error-only] [-i INPUT_FILE] [-o OUTPUT_FILE] [team_name]

Create the SecurityChampion Github Team.

positional arguments:
  team_name

options:
  -h, --help            show this help message and exit
  --debug               Display "debugging" in output (defaults to "info").
  --error-only          Display "error" in output only (filters "info").
  -i INPUT_FILE, --input-file INPUT_FILE
                        File contains list of Teams to be processed.
  -o OUTPUT_FILE, --output-result OUTPUT_FILE
                        Result of the run in CSV format.
```

```shell
export GITHUB_TOKEN=mytoken
export GITHUB_ORG=myorg
```

```shell
python github_add_team_securitychampion.py myteam1 myteam2 starfox
```

Example output
```shell
add_security_team:INFO:failed to locate team "myteam1"
add_security_team:INFO:failed to locate team "myteam2"
_add_child_team:INFO:security team "starfox_SecurityChampion" created successfully in the parent team "starfox_SecurityChampion"
```

## github_get_all_teams.py

Invoke the help argument

```shell
% python github_get_all_teams.py --help
usage: github_get_teams.py [-h] [--debug] [--error-only] [-p]

Get the names of Github teams.

options:
  -h, --help         show this help message and exit
  --debug            Display "debugging" in output (defaults to "info")
  --error-only       Display "error" in output only (filters "info")
  -p, --parent-only  Get Teams that are parent type only.
```


```shell
export GITHUB_TOKEN=mytoken
export GITHUB_ORG=myorg
```

```shell
python github_add_team_securitychampion.py 
```

Example output
```shell
[{'description': 'My team',
  'html_url': 'https://github.com/orgs/myorg/teams/myteam',
  'id': 123456,
  ...
  },
  ...
]
```