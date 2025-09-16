#!/usr/bin/env python3
"""
GitLab Cloner Main Class Tests

Copyright (c) 2025 Michele Tavella <meeghele@proton.me>
Licensed under the MIT License.

Author: Michele Tavella <meeghele@proton.me>
"""

import os
import sys
from unittest.mock import patch, Mock, MagicMock
import pytest

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module under test
import importlib.util
spec = importlib.util.spec_from_file_location("gitlab_cloner", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gitlab-cloner.py"))
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)


class TestGitLabCloner:
    """Test GitLabCloner main class."""
    
    def test_init(self):
        """Test GitLabCloner initialization."""
        config = gc.Config(
            url='https://gitlab.com',
            token='test-token', 
            namespace='test-ns',
            path='/test/path',
            disable_root=False,
            dry_run=False,
            exclude=None
        )
        
        cloner = gc.GitLabCloner(config)
        
        assert cloner.config == config
        assert cloner.gitlab_api is None
        assert cloner.projects == []
    
    @patch('os.path.isdir')
    @patch.object(gc.GitOperations, 'validate_git_available')
    @patch('gitlab.Gitlab')
    def test_validate_environment_success(self, mock_gitlab_class, mock_validate_git, mock_isdir):
        """Test successful environment validation."""
        mock_isdir.return_value = True
        
        config = gc.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns', 
            path='/test/path',
            disable_root=False,
            dry_run=False,
            exclude=None
        )
        
        cloner = gc.GitLabCloner(config)
        
        # Should not raise exception
        cloner._validate_environment()
        
        mock_isdir.assert_called_once_with('/test/path')
        mock_validate_git.assert_called_once()
    
    @patch('os.path.isdir')
    @patch('sys.exit')
    def test_validate_environment_path_not_exists(self, mock_exit, mock_isdir):
        """Test environment validation with invalid path."""
        mock_isdir.return_value = False
        
        config = gc.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            path='/nonexistent/path',
            disable_root=False,
            dry_run=False,
            exclude=None
        )
        
        cloner = gc.GitLabCloner(config)
        cloner._validate_environment()
        
        mock_exit.assert_called_once_with(gc.EXIT_PATH_ERROR)
    
    @patch('gitlab.Gitlab')
    def test_initialize_gitlab_api_success(self, mock_gitlab_class):
        """Test successful GitLab API initialization."""
        mock_api = Mock()
        mock_gitlab_class.return_value = mock_api
        
        config = gc.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            path='/test/path', 
            disable_root=False,
            dry_run=False,
            exclude=None
        )
        
        cloner = gc.GitLabCloner(config)
        cloner._initialize_gitlab_api()
        
        mock_gitlab_class.assert_called_once_with(
            url='https://gitlab.com', 
            private_token='test-token'
        )
        mock_api.auth.assert_called_once()
        assert cloner.gitlab_api == mock_api
    
    @patch('gitlab.Gitlab')
    @patch('sys.exit')
    def test_initialize_gitlab_api_failure(self, mock_exit, mock_gitlab_class):
        """Test GitLab API initialization failure."""
        mock_api = Mock()
        mock_api.auth.side_effect = Exception("Authentication failed")
        mock_gitlab_class.return_value = mock_api
        
        config = gc.Config(
            url='https://gitlab.com',
            token='invalid-token',
            namespace='test-ns',
            path='/test/path',
            disable_root=False,
            dry_run=False,
            exclude=None
        )
        
        cloner = gc.GitLabCloner(config)
        cloner._initialize_gitlab_api()
        
        mock_exit.assert_called_once_with(gc.EXIT_GITLAB_ERROR)
    
    @patch.object(gc.GitLabCloner, '_process_projects')
    @patch.object(gc.GitLabCloner, '_collect_projects')
    @patch.object(gc.GitLabCloner, '_initialize_gitlab_api')
    @patch.object(gc.GitLabCloner, '_validate_environment')
    def test_run_success(self, mock_validate, mock_init_api, mock_collect, mock_process):
        """Test successful run execution."""
        config = gc.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            path='/test/path',
            disable_root=False,
            dry_run=False,
            exclude=None
        )
        
        cloner = gc.GitLabCloner(config)
        result = cloner.run()
        
        assert result == gc.EXIT_SUCCESS
        mock_validate.assert_called_once()
        mock_init_api.assert_called_once()
        mock_collect.assert_called_once()
        mock_process.assert_called_once()
    
    @patch.object(gc.GitLabCloner, '_collect_projects')
    @patch.object(gc.GitLabCloner, '_initialize_gitlab_api')
    @patch.object(gc.GitLabCloner, '_validate_environment')
    def test_run_dry_run_mode(self, mock_validate, mock_init_api, mock_collect):
        """Test run execution in dry-run mode."""
        config = gc.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            path='/test/path',
            disable_root=False,
            dry_run=True,  # Dry run mode
            exclude=None
        )
        
        cloner = gc.GitLabCloner(config)
        result = cloner.run()
        
        assert result == gc.EXIT_SUCCESS
        mock_validate.assert_called_once()
        mock_init_api.assert_called_once()
        mock_collect.assert_called_once()
        # _process_projects should not be called in dry-run mode
    
    @patch.object(gc.GitLabCloner, '_validate_environment')
    def test_run_exception_handling(self, mock_validate):
        """Test run exception handling."""
        mock_validate.side_effect = Exception("Test error")

        config = gc.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            path='/test/path',
            disable_root=False,
            dry_run=False,
            exclude=None
        )

        cloner = gc.GitLabCloner(config)
        result = cloner.run()

        assert result == gc.EXIT_EXECUTION_ERROR

    def test_collect_projects_traverses_subgroups(self):
        """Ensure subgroup traversal does not rely on ownership filters."""
        config = gc.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            path='/test/path',
            disable_root=False,
            dry_run=False,
            exclude=None
        )

        cloner = gc.GitLabCloner(config)

        mock_api = Mock()
        mock_groups = Mock()
        mock_api.groups = mock_groups

        root_project = Mock()
        root_project.path_with_namespace = 'test-ns/root'
        subgroup_project = Mock()
        subgroup_project.path_with_namespace = 'test-ns/sub/repo'

        subgroup_stub = Mock()
        subgroup_stub.id = 123
        subgroup_stub.full_path = 'test-ns/sub'

        root_group = Mock()
        root_group.projects.list.return_value = [root_project]
        root_group.subgroups = Mock()
        root_group.subgroups.list.return_value = [subgroup_stub]

        subgroup_group = Mock()
        subgroup_group.projects.list.return_value = [subgroup_project]
        subgroup_group.subgroups = Mock()
        subgroup_group.subgroups.list.return_value = []

        def get_side_effect(identifier, **_kwargs):
            if identifier == 'test-ns':
                return root_group
            if identifier == 123:
                return subgroup_group
            raise AssertionError('unexpected group lookup')

        mock_groups.get.side_effect = get_side_effect
        cloner.gitlab_api = mock_api

        cloner._collect_projects()

        assert root_project in cloner.projects
        assert subgroup_project in cloner.projects
        assert len(cloner.projects) == 2


class TestMainFunction:
    """Test main function."""
    
    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        assert hasattr(gc, 'main')
        assert callable(gc.main)
    
    def test_parse_arguments_function_exists(self):
        """Test that parse_arguments function exists and is callable."""
        assert hasattr(gc, 'parse_arguments')
        assert callable(gc.parse_arguments)
