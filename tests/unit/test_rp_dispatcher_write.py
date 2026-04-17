"""
Unit tests for rptool write command.
"""

import pytest
from unittest.mock import patch, MagicMock, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from reportportal.rp_dispatcher import run_write_command
from reportportal.ap import create_main_parser


@pytest.mark.unit
class TestRunWriteCommand:
    """Test run_write_command function."""

    @patch('reportportal.rp_dispatcher.RPWriter')
    def test_run_write_command_success(self, mock_rpwriter):
        """Test successful write command execution."""
        # Setup mocks
        mock_writer_instance = MagicMock()
        mock_writer_instance.process_junit_file.return_value = 0
        mock_rpwriter.return_value = mock_writer_instance

        # Create args
        args = MagicMock()
        args.rp_url = 'https://rp.example.com'
        args.rp_project = 'test_project'
        args.rp_token = 'test_key'
        args.junits = ['test.xml']
        args.log_level = 'INFO'

        parser = MagicMock()

        # Execute
        result = run_write_command(args, parser)

        # Verify
        assert result == 0
        mock_rpwriter.assert_called_once_with(args)
        mock_writer_instance.process_junit_file.assert_called_once()

    @patch('reportportal.rp_dispatcher.RPWriter')
    def test_run_write_command_with_debug_logging(self, mock_rpwriter):
        """Test write command with DEBUG log level."""
        # Setup mocks
        mock_writer_instance = MagicMock()
        mock_writer_instance.process_junit_file.return_value = 0
        mock_rpwriter.return_value = mock_writer_instance

        # Create args with DEBUG log level
        args = MagicMock()
        args.rp_url = 'https://rp.example.com'
        args.rp_project = 'test_project'
        args.rp_token = 'test_key'
        args.junits = ['test.xml']
        args.log_level = 'DEBUG'

        parser = MagicMock()

        # Execute
        result = run_write_command(args, parser)

        # Verify
        assert result == 0

    def test_run_write_command_missing_endpoint(self):
        """Test write command with missing endpoint."""
        args = MagicMock()
        args.rp_url = None
        args.rp_project = 'test_project'
        args.rp_token = 'test_key'

        # Create a parser that raises SystemExit when error() is called
        parser = MagicMock()
        parser.error.side_effect = SystemExit(2)

        # Should call parser.error which raises SystemExit
        with pytest.raises(SystemExit):
            run_write_command(args, parser)

    def test_run_write_command_missing_project(self):
        """Test write command with missing project."""
        args = MagicMock()
        args.rp_url = 'https://rp.example.com'
        args.rp_project = None
        args.rp_token = 'test_key'

        # Create a parser that raises SystemExit when error() is called
        parser = MagicMock()
        parser.error.side_effect = SystemExit(2)

        # Should call parser.error which raises SystemExit
        with pytest.raises(SystemExit):
            run_write_command(args, parser)

    def test_run_write_command_missing_api_key(self):
        """Test write command with missing API key."""
        args = MagicMock()
        args.rp_url = 'https://rp.example.com'
        args.rp_project = 'test_project'
        args.rp_token = None

        # Create a parser that raises SystemExit when error() is called
        parser = MagicMock()
        parser.error.side_effect = SystemExit(2)

        # Should call parser.error which raises SystemExit
        with pytest.raises(SystemExit):
            run_write_command(args, parser)

    @patch('reportportal.rp_dispatcher.RPWriter')
    def test_run_write_command_missing_junit_file(self, mock_rpwriter):
        """Test write command with missing JUnit file."""
        args = MagicMock()
        args.rp_url = 'https://rp.example.com'
        args.rp_project = 'test_project'
        args.rp_token = 'test_key'
        args.junits = None
        args.log_level = 'INFO'

        parser = MagicMock()

        result = run_write_command(args, parser)

        assert result == 1
        # RPWriter should not be created
        mock_rpwriter.assert_not_called()

    @patch('reportportal.rp_dispatcher.RPWriter')
    def test_run_write_command_process_returns_error(self, mock_rpwriter):
        """Test write command when process_junit_file returns error."""
        mock_writer_instance = MagicMock()
        mock_writer_instance.process_junit_file.return_value = 1
        mock_rpwriter.return_value = mock_writer_instance

        args = MagicMock()
        args.rp_url = 'https://rp.example.com'
        args.rp_project = 'test_project'
        args.rp_token = 'test_key'
        args.junits = ['test.xml']
        args.log_level = 'INFO'

        parser = MagicMock()

        result = run_write_command(args, parser)

        # Should propagate error code from process_junit_file
        assert result == 1

    @patch('reportportal.rp_dispatcher.RPWriter')
    def test_run_write_command_exception_handling(self, mock_rpwriter):
        """Test write command exception handling."""
        mock_rpwriter.side_effect = Exception("Test error")

        args = MagicMock()
        args.rp_url = 'https://rp.example.com'
        args.rp_project = 'test_project'
        args.rp_token = 'test_key'
        args.junits = ['test.xml']
        args.log_level = 'INFO'

        parser = MagicMock()

        result = run_write_command(args, parser)

        assert result == 1

    @patch('reportportal.rp_dispatcher.RPWriter')
    def test_run_write_command_with_log_level(self, mock_rpwriter):
        """Test write command with log level."""
        mock_writer_instance = MagicMock()
        mock_writer_instance.process_junit_file.return_value = 0
        mock_rpwriter.return_value = mock_writer_instance

        # Create args with log_level
        args = MagicMock()
        args.rp_url = 'https://rp.example.com'
        args.rp_project = 'test_project'
        args.rp_token = 'test_key'
        args.junits = ['test.xml']
        args.log_level = 'INFO'

        parser = MagicMock()

        result = run_write_command(args, parser)

        # Should succeed
        assert result == 0


@pytest.mark.unit
class TestWriteCommandIntegration:
    """Test write command integration with main dispatcher."""

    @patch('reportportal.config.load_config_file')
    def test_write_command_registered(self, mock_load_config):
        """Test that write command is registered in dispatcher."""
        # Mock config file to isolate test from user's environment
        mock_load_config.return_value = {}

        parser = create_main_parser()

        # Parse write command help to verify it exists
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['write', '--help'])

        # --help should exit with code 0
        assert exc_info.value.code == 0

    @patch('reportportal.config.load_config_file')
    def test_write_command_arguments(self, mock_load_config):
        """Test parsing write command arguments."""
        # Mock config file to isolate test from user's environment
        mock_load_config.return_value = {}

        parser = create_main_parser()
        args = parser.parse_args([
            '--log-level', 'DEBUG',
            'write',
            '--rp-project', 'my_project',
            '--rp-url', 'https://rp.example.com',
            '--rp-token', 'my_key',
            '--launch-name', 'Test Launch',
            '--trigger-auto-analysis',
            'test.xml'
        ])

        assert args.command == 'write'
        assert args.rp_project == 'my_project'
        assert args.rp_url == 'https://rp.example.com'
        assert args.rp_token == 'my_key'
        assert args.log_level == 'DEBUG'
        assert args.launch_name == 'Test Launch'
        assert args.trigger_auto_analysis is True
        assert args.junits == ['test.xml']

    @patch('reportportal.config.load_config_file')
    def test_write_command_missing_junit_file(self, mock_load_config):
        """Test that missing JUnit file raises error."""
        # Mock config file to isolate test from user's environment
        mock_load_config.return_value = {}

        parser = create_main_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['write'])

        # Should exit with error code
        assert exc_info.value.code != 0
