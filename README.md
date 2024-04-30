# github_tools

## github_add_team_securitychampion.py

Invoke the help argument

Personal Access Token (PAT) requires the following permissions:
- admin:org: write:org, read:org

Remember to *authorize* in org if SSO is used.

```shell
% python github_add_team_securitychampion.py --help
usage: github_add_team_securitychampion.py [-h] [--debug] [--error-only] team_parent_name [team_parent_name ...]

Create an Archive BitBucket Project

positional arguments:
  team_parent_name

options:
  -h, --help        show this help message and exit
  --debug           Display "debugging" in output (defaults to "info")
  --error-only      Display "error" in output only (filters "info")
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
usage: github_get_all_teams.py [-h] [--debug] [--error-only]

Get all Github teams and output in Python format

options:
  -h, --help    show this help message and exit
  --debug       Display "debugging" in output (defaults to "info")
  --error-only  Display "error" in output only (filters "info")
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