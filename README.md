# github_tools

## Example end-to-end testing

### 1) Export the required environment variables

We need to export the required environment variables:

```shell
export GITHUB_TOKEN=mytoken
export GITHUB_ORG=myorg
```

### 2) Get the Github Teams to be processed

We need to get all Github Teams that : 
 - are "parent" type AND 
 - are the parents of the "XYZ_Admin" and "XYZ_User" child Teams

```shell
python github_get_securitychampion_parent_teams.py > queue_securitychampion_parent_teams.txt
```

### 3) Create the SecurityChampion teams

Let's go ahead and create the "SecurityChampion" team from the input list: **queue_securitychampion_parent_teams.txt**
 - Each run will create a log file (e.g. github_add_team_securitychampion.py.2024-05-14_17:59:46-447753.log)
 - the parameter "-o run_securitychamption_result.csv" will create a csv file containing the result of each item

```shell
python github_add_securitychampion_team.py -i queue_securitychampion_parent_teams.txt -o run_securitychamption.result.csv
```

An example output of the **run_securitychamption.result.csv** file (which can be easily imported to Excel):

```shell
TEAM_NAME,RUN_OK
Banana,False
Strawberry,False
StarfoxHUB_1010,True
Apple,False
```

An example log of the run: **github_add_securitychampion_team.py.2024-05-14_18:29:05-266219.log**

```shell
add_security_team:ERROR:failed to locate team "Banana"
add_security_team:ERROR:failed to locate team "Strawberry"
_add_child_team:INFO:OK:security team "StarfoxHUB_1010_SecurityChampion" created successfully
add_security_team:ERROR:failed to locate team "Apple"
```

### 4) Generate a list of Teams for Maintainers members to be copied

Let's go ahead and generate an input list of "parent" Teams' Maintainers to be copied to the SecurityChamption Teams
 - output a new queue called: **queue_securitychampion_maintainer_copy.txt**

```shell
python generate_teams_maintainer_list.py queue_securitychampion_parent_teams.txt | tee queue_securitychampion_maintainer_copy.txt
```

An example output of the **run_maintainer_copy.result.csv** file (which can be easily imported to Excel):

```shell
SOURCE_TEAM,DESTINATION_TEAM
Banana,Banana_SecurityChampion
Strawberry,Strawberry_SecurityChampion
StarfoxHUB_1010,StarfoxHUB_1010_SecurityChampion
Apple,Apple_SecurityChampion
```

### 5) Copy Maintainers from Parent Teams to SecurityChampion Teams

Let's process the list:
 - Copy the Maintainer members from SOURCE_TEAM to DESTINATON_TEAM

```shell
python github_copy_maintainers.py -i queue_securitychampion_maintainer_copy.txt -o run_maintainer_copy.result.csv
```

An example output of the **run_maintainer_copy.result.csv** file (which can be easily imported to Excel):

```shell
SOURCE_TEAM,DESTINATION_TEAM,RUN_OK
Banana,Banana_SecurityChampion,False
Strawberry,Strawberry_SecurityChampion,False
StarfoxHUB_1010,StarfoxHUB_1010_SecurityChampion,True
Apple,Apple_SecurityChampion,False
```

An example log of the run: **github_add_securitychampion_team.py.2024-05-14_18:29:05-266219.log**

```shell
add_security_team:ERROR:failed to locate team "Banana"
add_security_team:ERROR:failed to locate team "Strawberry"
_add_child_team:INFO:OK:security team "StarfoxHUB_1010_SecurityChampion" created successfully
add_security_team:ERROR:failed to locate team "Apple"
```

An example log:

```shell
SOURCE_TEAM,DESTINATION_TEAM,RUN_OK
Banana,Banana_SecurityChampion,False
Strawberry,Strawberry_SecurityChampion,False
StarfoxHUB_1010,StarfoxHUB_1010_SecurityChampion,True
Apple,Apple_SecurityChampion,False
```

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