[![CI](https://github.com/meeghele/gitlab-cloner/actions/workflows/ci.yml/badge.svg)](https://github.com/meeghele/gitlab-cloner/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# GitLab Cloner

<div align="center">
  <img src="images/gitlab-cloner_512.jpg" alt="GitLab Cloner Logo" width="200"/>
</div>

A Python command-line tool that automates the process of cloning or fetching all repositories from a GitLab namespace, including subgroups and their projects.

## Features

- **Complete namespace cloning**: Clone all repositories under a specified GitLab namespace, including all nested subgroups
- **Smart sync**: If a repository is not cloned already, it will be cloned; if it exists, it will be fetched
- **Exclusion patterns**: Option to exclude specific subgroups or projects based on name patterns
- **Dry-run mode**: List all repositories without actually cloning or fetching them
- **Flexible destination**: Configurable destination path for cloned repositories
- **Namespace handling**: Option to disable root namespace folder creation
- **Robust error handling**: Clear error messages and appropriate exit codes
- **Colored output**: Terminal color output for better readability

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python gitlab-cloner.py -n NAMESPACE [options]
```

### Authentication

Set your GitLab token using one of these methods:

1. **Environment variable (recommended):**
   ```bash
   export GITLAB_TOKEN=your-api-token
   python gitlab-cloner.py -n your-namespace
   ```

2. **Command line argument:**
   ```bash
   python gitlab-cloner.py -n your-namespace -t your-api-token
   ```

### Command Line Options

| Option | Long Option | Description |
|--------|-------------|-------------|
| `-u` | `--url` | Base URL of the GitLab instance (default: `https://gitlab.com`) |
| `-t` | `--token` | GitLab API token (can also use `GITLAB_TOKEN` env var) |
| `-n` | `--namespace` | **Required.** Namespace (group) to clone |
| `-p` | `--path` | Destination path for cloned projects (default: current directory) |
| | `--disable-root` | Do not create root namespace folder in path |
| `-d` | `--dry-run` | List repositories without clone/fetch |
| `-e` | `--exclude` | Pattern to exclude from subgroups and projects |
| `-h` | `--help` | Show help message and exit |

## Examples

**Basic usage:**
```bash
python gitlab-cloner.py -n mygroup
```

**Clone to specific directory:**
```bash
python gitlab-cloner.py -n mygroup -p /path/to/repos
```

**Dry run to see what would be cloned:**
```bash
python gitlab-cloner.py -n mygroup --dry-run
```

**Exclude projects containing "archived":**
```bash
python gitlab-cloner.py -n mygroup --exclude archived
```

**Use custom GitLab instance:**
```bash
python gitlab-cloner.py -n mygroup -u https://gitlab.company.com
```

**Disable root folder creation:**
```bash
python gitlab-cloner.py -n mygroup --disable-root
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Execution error |
| 2 | Missing required arguments |
| 10 | Destination path error |
| 20 | Git executable not found |
| 21 | Git clone error |
| 22 | Git fetch error |
| 30 | GitLab API error |
| 40 | Authentication error |

## Token Permissions

Your GitLab token needs:
- **Scope**: `read_repository` 
- **Role**: Reporter or higher on the target namespace

Create a token at your GitLab instance under User Settings > Access Tokens.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome, please follow the semantic versioning branch naming convention:

- **main**: Production-ready code
- **develop**: Integration branch for features
- **feat/**: New features (`feat/user-authentication`)
- **fix/**: Bug fixes (`fix/connection-timeout`)
- **chore/**: Maintenance (`chore/update-dependencies`)
