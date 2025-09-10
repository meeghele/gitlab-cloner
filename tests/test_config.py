#!/usr/bin/env python3
"""
GitLab Cloner Configuration Tests

Copyright (c) 2025 Michele Tavella <meeghele@proton.me>
Licensed under the MIT License.

Author: Michele Tavella <meeghele@proton.me>
"""

import os
import sys
from unittest.mock import patch, Mock
import pytest

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module under test
import importlib.util
spec = importlib.util.spec_from_file_location("gitlab_cloner", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gitlab-cloner.py"))
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)


class TestConfig:
    """Test configuration management."""
    
    def test_config_creation(self):
        """Test Config dataclass creation."""
        config = gc.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            path='/test/path',
            disable_root=False,
            dry_run=False,
            exclude='repo1'
        )
        
        assert config.url == 'https://gitlab.com'
        assert config.token == 'test-token'
        assert config.namespace == 'test-ns'
        assert config.path == '/test/path'
        assert config.disable_root is False
        assert config.dry_run is False
        assert config.exclude == 'repo1'
    
    def test_config_defaults(self):
        """Test Config with None exclude."""
        config = gc.Config(
            url='https://gitlab.com',
            token='test-token',
            namespace='test-ns',
            path='/test/path',
            disable_root=False,
            dry_run=False,
            exclude=None
        )
        
        assert config.exclude is None
        assert config.disable_root is False
        assert config.dry_run is False


class TestArgumentParsing:
    """Test command-line argument parsing."""
    
    def test_parse_args_minimal(self):
        """Test parsing minimal required arguments."""
        args = [
            '--token', 'test-token',
            '--namespace', 'test-ns',
            '--path', '/test/path'
        ]
        
        with patch('sys.argv', ['gitlab-cloner.py'] + args):
            config = gc.parse_arguments()
            
        assert config.token == 'test-token'
        assert config.namespace == 'test-ns'
        assert config.path == '/test/path'
        assert config.url == 'https://gitlab.com'
        assert config.exclude is None
        assert config.dry_run is False
        assert config.disable_root is False
    
    def test_parse_args_all_options(self):
        """Test parsing all available arguments."""
        args = [
            '--url', 'https://gitlab.example.com',
            '--token', 'test-token',
            '--namespace', 'test-ns',
            '--path', '/test/path',
            '--exclude', 'repo1',
            '--dry-run',
            '--disable-root'
        ]
        
        with patch('sys.argv', ['gitlab-cloner.py'] + args):
            config = gc.parse_arguments()
            
        assert config.url == 'https://gitlab.example.com'
        assert config.token == 'test-token'
        assert config.namespace == 'test-ns'
        assert config.path == '/test/path'
        assert config.exclude == 'repo1'
        assert config.dry_run is True
        assert config.disable_root is True
    
    @patch.dict(os.environ, {'GITLAB_TOKEN': 'env-token'})
    def test_token_from_environment(self):
        """Test token reading from environment variable."""
        args = [
            '--namespace', 'test-ns',
            '--path', '/test/path'
        ]
        
        with patch('sys.argv', ['gitlab-cloner.py'] + args):
            config = gc.parse_arguments()
            
        assert config.token == 'env-token'
    
    def test_parse_args_missing_token_no_env(self):
        """Test parsing fails when token is missing and no env var."""
        args = [
            '--namespace', 'test-ns',
            '--path', '/test/path'
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('sys.argv', ['gitlab-cloner.py'] + args):
                with pytest.raises(SystemExit) as exc_info:
                    gc.parse_arguments()
                
                assert exc_info.value.code == gc.EXIT_AUTH_ERROR


class TestLogger:
    """Test Logger class functionality."""
    
    def test_logger_debug(self, capsys):
        """Test Logger.debug method."""
        gc.Logger.debug("debug message")
        
        captured = capsys.readouterr()
        assert "debug message" in captured.out
    
    def test_logger_info(self, capsys):
        """Test Logger.info method."""
        gc.Logger.info("info message")
        
        captured = capsys.readouterr()
        assert "info message" in captured.out
    
    def test_logger_warn(self, capsys):
        """Test Logger.warn method."""
        gc.Logger.warn("warning message")
        
        captured = capsys.readouterr()
        assert "warning message" in captured.out
    
    def test_logger_error(self, capsys):
        """Test Logger.error method."""
        gc.Logger.error("error message")
        
        captured = capsys.readouterr()
        assert "error message" in captured.err


class TestPathManager:
    """Test PathManager class functionality."""
    
    def test_calculate_local_path_basic(self):
        """Test basic local path calculation."""
        result = gc.PathManager.calculate_local_path(
            project_path="mygroup/myproject",
            base_path="/repos",
            namespace="mygroup", 
            disable_root=False
        )
        
        expected = os.path.normpath("/repos/mygroup/myproject")
        assert result == expected
    
    def test_calculate_local_path_disable_root(self):
        """Test local path calculation with disable_root=True."""
        result = gc.PathManager.calculate_local_path(
            project_path="mygroup/myproject",
            base_path="/repos",
            namespace="mygroup",
            disable_root=True
        )
        
        expected = os.path.normpath("/repos/myproject")
        assert result == expected
    
    def test_ensure_parent_directories(self, tmp_path):
        """Test parent directory creation."""
        test_file_path = tmp_path / "subdir" / "file.txt"
        
        gc.PathManager.ensure_parent_directories(str(test_file_path))
        
        assert test_file_path.parent.exists()
        assert test_file_path.parent.is_dir()


class TestGitOperations:
    """Test GitOperations class functionality."""
    
    @patch('shutil.which')
    def test_validate_git_available_success(self, mock_which):
        """Test successful git validation."""
        mock_which.return_value = '/usr/bin/git'
        
        # Should not raise an exception
        gc.GitOperations.validate_git_available()
    
    @patch('shutil.which') 
    @patch('sys.exit')
    def test_validate_git_available_failure(self, mock_exit, mock_which):
        """Test git validation failure."""
        mock_which.return_value = None
        
        gc.GitOperations.validate_git_available()
        
        mock_exit.assert_called_once_with(gc.EXIT_GIT_NOT_FOUND)
    
    @patch('subprocess.run')
    def test_clone_repository_success(self, mock_run):
        """Test successful repository cloning."""
        mock_run.return_value.returncode = 0
        
        # Should not raise an exception
        gc.GitOperations.clone_repository('https://example.com/repo.git', '/local/path')
        
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    @patch('sys.exit')
    def test_clone_repository_failure(self, mock_exit, mock_run):
        """Test repository cloning failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = 'Clone failed'
        
        gc.GitOperations.clone_repository('https://example.com/repo.git', '/local/path')
        
        mock_exit.assert_called_once_with(gc.EXIT_GIT_CLONE_ERROR)
    
    @patch('subprocess.run')
    def test_fetch_repository_success(self, mock_run):
        """Test successful repository fetching."""
        mock_run.return_value.returncode = 0
        
        # Should not raise an exception
        gc.GitOperations.fetch_repository('/local/path')
        
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    @patch('sys.exit')
    def test_fetch_repository_failure(self, mock_exit, mock_run):
        """Test repository fetching failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = 'Fetch failed'
        
        gc.GitOperations.fetch_repository('/local/path')
        
        mock_exit.assert_called_once_with(gc.EXIT_GIT_FETCH_ERROR)