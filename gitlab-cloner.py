#!/usr/bin/env python3
"""
GitLab Cloner - Clone and manage all repositories from a GitLab namespace.

This tool automates the process of cloning or fetching all repositories from
a GitLab namespace, including all nested subgroups. It provides intelligent
sync capabilities, exclusion patterns, and dry-run functionality.

Copyright (c) 2025 Michele Tavella <meeghele@proton.me>
Licensed under the MIT License. See LICENSE file for details.

Author: Michele Tavella <meeghele@proton.me>
License: MIT
"""

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import List, NoReturn, Optional

import colorama
import gitlab

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)

# Exit codes
EXIT_SUCCESS = 0
EXIT_EXECUTION_ERROR = 1
EXIT_MISSING_ARGUMENTS = 2
EXIT_PATH_ERROR = 10
EXIT_GIT_NOT_FOUND = 20
EXIT_GIT_CLONE_ERROR = 21
EXIT_GIT_FETCH_ERROR = 22
EXIT_GITLAB_ERROR = 30
EXIT_AUTH_ERROR = 40


class CloneMethod(Enum):
    """Enumeration for git clone methods."""

    HTTPS = "https"
    SSH = "ssh"


@dataclass
class Config:  # pylint: disable=too-many-instance-attributes
    """Configuration for GitLab cloner."""

    url: str
    token: str
    namespace: str
    path: str
    disable_root: bool
    dry_run: bool
    exclude: Optional[str]
    clone_method: CloneMethod = CloneMethod.HTTPS


class GitOperations:
    """Handles Git operations like clone and fetch."""

    @staticmethod
    def validate_git_available() -> None:
        """Validate that git executable is available."""
        git_executable = shutil.which("git")
        if git_executable is None:
            Logger.error("error: git executable not installed or not in $PATH")
            sys.exit(EXIT_GIT_NOT_FOUND)
        Logger.debug(f"git: {git_executable}")

    @staticmethod
    def clone_repository(remote_url: str, local_path: str) -> None:
        """Clone a repository."""
        Logger.debug(f"cloning: {remote_url}")
        try:
            result = subprocess.run(
                ["git", "clone", remote_url, local_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                Logger.error(f"git clone failed: {result.stderr}")
                sys.exit(EXIT_GIT_CLONE_ERROR)
        except Exception as e:
            Logger.error(f"unexpected error while cloning: {e}")
            sys.exit(EXIT_GIT_CLONE_ERROR)

    @staticmethod
    def fetch_repository(local_path: str) -> None:
        """Fetch updates for existing repository."""
        Logger.debug(f"fetching: {local_path}")
        try:
            result = subprocess.run(
                ["git", "-C", local_path, "fetch", "--all"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                Logger.error(f"git fetch failed: {result.stderr}")
                sys.exit(EXIT_GIT_FETCH_ERROR)
        except Exception as e:
            Logger.error(f"unexpected error while fetching: {e}")
            sys.exit(EXIT_GIT_FETCH_ERROR)


class PathManager:
    """Handles path operations and calculations."""

    @staticmethod
    def ensure_parent_directories(path: str) -> None:
        """Create parent directories if they don't exist."""
        parent_dir = os.path.dirname(path)
        os.makedirs(parent_dir, exist_ok=True)

    @staticmethod
    def calculate_local_path(
        project_path: str, base_path: str, namespace: str, disable_root: bool
    ) -> str:
        """Calculate local path for project."""
        folders = [f.strip().lower() for f in project_path.split("/")]

        if disable_root:
            namespace_lower = namespace.lower()
            if namespace_lower in folders:
                folders.remove(namespace_lower)

        local_path = os.path.join(base_path, *folders)
        return os.path.normpath(local_path)


class Logger:
    """Handles formatted console output with colors."""

    PROCESS_NAME = "gitlab-cloner"

    @classmethod
    def debug(cls, *messages: str) -> None:
        """Print debug message in gray."""
        cls._write_stdout(colorama.Fore.LIGHTBLACK_EX, *messages)

    @classmethod
    def info(cls, *messages: str) -> None:
        """Print info message in blue."""
        cls._write_stdout(colorama.Fore.BLUE, *messages)

    @classmethod
    def warn(cls, *messages: str) -> None:
        """Print warning message in yellow."""
        cls._write_stdout(colorama.Fore.YELLOW, *messages)

    @classmethod
    def error(cls, *messages: str) -> None:
        """Print error message in red to stderr."""
        cls._write_stderr(colorama.Fore.RED, *messages)

    @classmethod
    def _write_stdout(cls, color: str, *messages: str) -> None:
        """Write formatted message to stdout."""
        sys.stdout.write(cls._format_line(color, *messages) + "\n")

    @classmethod
    def _write_stderr(cls, color: str, *messages: str) -> None:
        """Write formatted message to stderr."""
        sys.stderr.write(cls._format_line(color, *messages) + "\n")

    @classmethod
    def _get_header(cls) -> str:
        """Get process header with PID."""
        return f"[{cls.PROCESS_NAME}:{os.getpid()}]"

    @classmethod
    def _format_line(cls, color: str, *messages: str) -> str:
        """Format a colored line with header."""
        header = cls._get_header()
        message = " ".join(str(msg) for msg in messages)
        return f"{color}{header}{colorama.Style.RESET_ALL} {message}"


class GitLabCloner:
    """Main class for cloning GitLab repositories."""

    def __init__(self, config: Config):
        """Initialize GitLab cloner with configuration."""
        self.config = config
        self.gitlab_api: Optional[gitlab.Gitlab] = None
        self.projects: List[object] = []

    def run(self) -> int:
        """Execute the cloning process."""
        try:
            self._validate_environment()
            self._initialize_gitlab_api()
            self._collect_projects()

            if self.config.dry_run:
                Logger.info("dry-run completed")
                return EXIT_SUCCESS

            self._process_projects()
            Logger.info("mission accomplished")
            return EXIT_SUCCESS

        except SystemExit as e:
            return int(e.code) if isinstance(e.code, int) else EXIT_EXECUTION_ERROR
        except Exception as e:
            Logger.error(f"unexpected error: {e}")
            return EXIT_EXECUTION_ERROR

    def _validate_environment(self) -> None:
        """Validate environment and requirements."""
        # Check destination path
        if not os.path.isdir(self.config.path):
            Logger.error(f"error: destination path does not exist: {self.config.path}")
            sys.exit(EXIT_PATH_ERROR)
        Logger.debug(f"path: {self.config.path}")

        # Check git executable
        GitOperations.validate_git_available()

    def _initialize_gitlab_api(self) -> None:
        """Initialize GitLab API connection."""
        Logger.info(f"init gitlab API: {self.config.url}")
        try:
            self.gitlab_api = gitlab.Gitlab(
                url=self.config.url, private_token=self.config.token
            )
            # Test authentication
            self.gitlab_api.auth()
        except gitlab.exceptions.GitlabAuthenticationError as e:
            Logger.error(f"authentication error: {e}")
            sys.exit(EXIT_AUTH_ERROR)
        except Exception as e:
            Logger.error(f"failed to initialize gitlab API: {e}")
            sys.exit(EXIT_GITLAB_ERROR)

    def _collect_projects(self) -> None:
        """Collect all projects from namespace and subgroups."""
        Logger.info(f"getting root groups: {self.config.namespace}")

        if self.gitlab_api is None:
            Logger.error("gitlab API not initialized")
            sys.exit(EXIT_GITLAB_ERROR)

        try:
            # Get root group
            root_group = self.gitlab_api.groups.get(
                self.config.namespace, lazy=False, include_subgroups=True
            )

            # Get projects from root group
            Logger.info("getting root projects")
            self._add_projects_from_group(root_group)

            # Get subgroups and their projects
            Logger.info("getting sub-groups")
            self._process_subgroups(root_group)

        except gitlab.exceptions.GitlabGetError as e:
            Logger.error(f"failed to get namespace '{self.config.namespace}': {e}")
            sys.exit(EXIT_GITLAB_ERROR)
        except Exception as e:
            Logger.error(f"unexpected error while collecting projects: {e}")
            sys.exit(EXIT_GITLAB_ERROR)

    def _add_projects_from_group(self, group: object) -> None:
        """Add all projects from a group."""
        try:
            for project in getattr(group, "projects").list(all=True):
                self.projects.append(project)
                Logger.debug(
                    f"found: {getattr(project, 'path_with_namespace', 'unknown')}"
                )
        except Exception as e:
            Logger.error(f"error getting projects from group: {e}")
            raise

    def _process_subgroups(self, root_group: object) -> None:
        """Recursively process all subgroups."""
        if self.gitlab_api is None:
            Logger.error("gitlab API not initialized")
            sys.exit(EXIT_GITLAB_ERROR)

        try:
            to_visit = []
            visited = set()

            subgroups_manager = getattr(root_group, "subgroups", None)
            if subgroups_manager is not None:
                to_visit.extend(subgroups_manager.list(all=True, recursive=True))

            while to_visit:
                subgroup = to_visit.pop(0)
                subgroup_id = getattr(subgroup, "id", None)
                if subgroup_id is None or subgroup_id in visited:
                    continue

                visited.add(subgroup_id)
                subgroup_path = getattr(subgroup, "full_path", "")
                if self._is_excluded(subgroup_path):
                    Logger.warn(f"excluding: {subgroup_path}")
                    continue

                full_group = self.gitlab_api.groups.get(subgroup_id, lazy=False)
                self._add_projects_from_group(full_group)

        except Exception as e:
            Logger.error(f"error processing subgroups: {e}")
            sys.exit(EXIT_GITLAB_ERROR)

    def _is_excluded(self, path: str) -> bool:
        """Check if path matches exclusion pattern."""
        if self.config.exclude:
            return self.config.exclude in path
        return False

    def _process_projects(self) -> None:
        """Clone or fetch all collected projects."""
        for project in self.projects:
            self._process_single_project(project)

    def _process_single_project(self, project: object) -> None:
        """Process a single project - clone or fetch."""
        project_path = getattr(project, "path_with_namespace", "unknown")
        Logger.info(f"processing: {project_path}")

        # Get project paths
        if self.config.clone_method == CloneMethod.SSH:
            remote_url = getattr(project, "ssh_url_to_repo", "")
        else:
            remote_url = getattr(project, "http_url_to_repo", "")
        local_path = PathManager.calculate_local_path(
            project_path,
            self.config.path,
            self.config.namespace,
            self.config.disable_root,
        )

        Logger.debug(f"remote: {remote_url}")
        Logger.debug(f"path: {local_path}")

        # Create parent directories
        PathManager.ensure_parent_directories(local_path)

        # Clone or fetch
        if not os.path.isdir(local_path):
            GitOperations.clone_repository(remote_url, local_path)
        else:
            GitOperations.fetch_repository(local_path)


def parse_arguments() -> Config:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Clone all repositories from a GitLab namespace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -n mygroup
  %(prog)s -n mygroup -p /path/to/repos --dry-run
  %(prog)s -n mygroup --exclude archived
        """,
    )

    parser.add_argument(
        "-u",
        "--url",
        dest="url",
        default="https://gitlab.com",
        help="Base URL of the GitLab instance (default: https://gitlab.com)",
    )

    parser.add_argument(
        "-t",
        "--token",
        dest="token",
        help="GitLab API token (can also use GITLAB_TOKEN env var)",
    )

    parser.add_argument(
        "-n",
        "--namespace",
        dest="namespace",
        required=True,
        help="Namespace (group) to clone",
    )

    parser.add_argument(
        "-p",
        "--path",
        dest="path",
        default=os.getcwd(),
        help="Destination path for cloned projects (default: current directory)",
    )

    parser.add_argument(
        "--disable-root",
        action="store_true",
        dest="disable_root",
        help="Do not create root namespace folder in path",
    )

    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="List the repositories without clone/fetch",
    )

    parser.add_argument(
        "-e",
        "--exclude",
        dest="exclude",
        help="Pattern to exclude from subgroups and projects",
    )

    parser.add_argument(
        "--clone-method",
        dest="clone_method",
        choices=[method.value for method in CloneMethod],
        default=CloneMethod.HTTPS.value,
        help="Clone method: https or ssh (default: https)",
    )

    args = parser.parse_args()

    # Handle token
    token = args.token or os.getenv("GITLAB_TOKEN")
    if not token:
        Logger.error(
            "error: gitlab token not provided. "
            "use -t or set GITLAB_TOKEN environment variable"
        )
        sys.exit(EXIT_AUTH_ERROR)

    if args.token:
        Logger.warn(
            "warning: token provided via command line argument "
            "(consider using environment variable)"
        )

    return Config(
        url=args.url,
        token=token,
        namespace=args.namespace,
        path=args.path,
        disable_root=args.disable_root,
        dry_run=args.dry_run,
        exclude=args.exclude,
        clone_method=CloneMethod(args.clone_method),
    )


def main() -> NoReturn:
    """Main entry point."""
    if __name__ != "__main__":
        sys.exit(EXIT_EXECUTION_ERROR)

    config = parse_arguments()
    cloner = GitLabCloner(config)
    sys.exit(cloner.run())


if __name__ == "__main__":
    main()
