#!/usr/bin/env python3
"""
GitLab Cloner Test Configuration and Fixtures

Copyright (c) 2025 Michele Tavella <meeghele@proton.me>
Licensed under the MIT License.

Author: Michele Tavella <meeghele@proton.me>
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock
from typing import Dict, List, Any

import pytest
import gitlab


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_config():
    """Provide a mock configuration for testing."""
    return {
        'url': 'https://gitlab.example.com',
        'token': 'test-token-123',
        'namespace': 'test-namespace',
        'path': '/tmp/test-path',
        'exclude': ['excluded-repo'],
        'dry_run': False,
        'verbose': False
    }


@pytest.fixture
def mock_gitlab_client():
    """Provide a mock GitLab client."""
    client = Mock(spec=gitlab.Gitlab)
    client.auth.return_value = None
    return client


@pytest.fixture
def mock_project():
    """Provide a mock GitLab project."""
    project = Mock()
    project.id = 1
    project.name = 'test-project'
    project.path = 'test-project'
    project.ssh_url_to_repo = 'git@gitlab.example.com:test-namespace/test-project.git'
    project.http_url_to_repo = 'https://gitlab.example.com/test-namespace/test-project.git'
    project.namespace = {'full_path': 'test-namespace'}
    return project


@pytest.fixture
def mock_group():
    """Provide a mock GitLab group."""
    group = Mock()
    group.id = 1
    group.name = 'test-group'
    group.full_path = 'test-namespace'
    group.projects = Mock()
    group.subgroups = Mock()
    return group


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess calls."""
    mock_run = Mock()
    mock_run.returncode = 0
    mock_run.stdout = ''
    mock_run.stderr = ''
    
    def mock_subprocess_run(*args, **kwargs):
        return mock_run
    
    monkeypatch.setattr('subprocess.run', mock_subprocess_run)
    return mock_run


@pytest.fixture
def sample_projects():
    """Provide sample project data for testing."""
    return [
        {
            'id': 1,
            'name': 'project1',
            'path': 'project1',
            'ssh_url_to_repo': 'git@gitlab.example.com:test/project1.git',
            'namespace': {'full_path': 'test'}
        },
        {
            'id': 2,
            'name': 'project2',
            'path': 'project2',
            'ssh_url_to_repo': 'git@gitlab.example.com:test/project2.git',
            'namespace': {'full_path': 'test'}
        }
    ]