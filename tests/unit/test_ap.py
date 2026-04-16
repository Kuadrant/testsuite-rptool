"""
Unit tests for ap (argument parser) module.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch

from reportportal.ap import (
    _get_config_defaults,
    create_main_parser,
    _add_write_arguments,
    _add_trigger_arguments,
    _add_summary_arguments,
)


@pytest.mark.unit
class TestEnvironmentDefaults:
    """Test environment variable parsing."""

    def test_get_env_defaults_no_env_vars(self):
        """Test defaults when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                defaults = _get_config_defaults()

                assert defaults['rp_url'] is None
                assert defaults['rp_token'] is None
                assert defaults['rp_project'] is None
                assert defaults['trigger_auto_analysis'] is False
                assert defaults['rp_launch_name'] is None
                assert defaults['rp_launch_description'] == ""

    def test_get_env_defaults_with_env_vars(self):
        """Test defaults when environment variables are set."""
        env_vars = {
            'RP_URL': 'https://custom.reportportal.com',
            'RP_TOKEN': 'test_api_key',
            'RP_PROJECT': 'test_project',
            'TRIGGER_AUTO_ANALYSIS': 'true',
            'RP_LAUNCH_NAME': 'Test Launch',
            'RP_LAUNCH_DESCRIPTION': 'Test Description'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                defaults = _get_config_defaults()

                assert defaults['rp_url'] == 'https://custom.reportportal.com'
                assert defaults['rp_token'] == 'test_api_key'
                assert defaults['rp_project'] == 'test_project'
                assert defaults['trigger_auto_analysis'] is True
                assert defaults['rp_launch_name'] == 'Test Launch'
                assert defaults['rp_launch_description'] == 'Test Description'

    def test_trigger_auto_analysis_env_var_parsing(self):
        """Test TRIGGER_AUTO_ANALYSIS environment variable parsing."""
        # Test various true values
        true_values = ['true', 'TRUE', '1', 'yes', 'YES', 'on', 'ON']
        for value in true_values:
            with patch.dict(os.environ, {'TRIGGER_AUTO_ANALYSIS': value}, clear=True):
                with patch('reportportal.config.load_config_file') as mock_load:
                    mock_load.return_value = {}
                    defaults = _get_config_defaults()
                    assert defaults['trigger_auto_analysis'] is True, f"Failed for value: {value}"

        # Test various false values
        false_values = ['false', 'FALSE', '0', 'no', 'NO', 'off', 'OFF', 'random', '']
        for value in false_values:
            with patch.dict(os.environ, {'TRIGGER_AUTO_ANALYSIS': value}, clear=True):
                with patch('reportportal.config.load_config_file') as mock_load:
                    mock_load.return_value = {}
                    defaults = _get_config_defaults()
                    assert defaults['trigger_auto_analysis'] is False, f"Failed for value: {value}"


@pytest.mark.unit
class TestArgumentParser:
    """Test argument parser functionality for write subcommand."""

    def test_get_argument_parser_basic(self):
        """Test basic argument parser creation for write command."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Test parsing with minimal arguments
                args = parser.parse_args(['write', 'test_junit.xml'])

                assert args.command == 'write'
                assert args.junits == ['test_junit.xml']
                assert args.rp_url is None
                assert args.trigger_auto_analysis is False  # Default value

    def test_trigger_auto_analysis_cli_argument(self):
        """Test --trigger-auto-analysis CLI argument."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Test without the flag
                args = parser.parse_args(['write', 'test_junit.xml'])
                assert args.trigger_auto_analysis is False

                # Test with the flag
                args = parser.parse_args(['write', '--trigger-auto-analysis', 'test_junit.xml'])
                assert args.trigger_auto_analysis is True

    def test_trigger_auto_analysis_env_var_override(self):
        """Test that environment variable sets default for trigger_auto_analysis."""
        # Set environment variable to true
        env_vars = {'TRIGGER_AUTO_ANALYSIS': 'true'}

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Environment variable sets default to True
                args = parser.parse_args(['write', 'test_junit.xml'])
                assert args.trigger_auto_analysis is True

    def test_all_arguments_present(self):
        """Test parser with all arguments."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                args = parser.parse_args([
                    'write',
                    '--rp-project', 'test_project',
                    '--rp-url', 'https://test.reportportal.com',
                    '--rp-token', 'test_key',
                    '--launch-name', 'Custom Launch',
                    '--launch-description', 'Custom Description',
                    '--trigger-auto-analysis',
                    'test_junit.xml'
                ])

                assert args.command == 'write'
                assert args.rp_project == 'test_project'
                assert args.rp_url == 'https://test.reportportal.com'
                assert args.rp_token == 'test_key'
                assert args.launch_name == 'Custom Launch'
                assert args.launch_description == 'Custom Description'
                assert args.trigger_auto_analysis is True
                assert args.junits == ['test_junit.xml']


@pytest.mark.unit
class TestTriggerParser:
    """Test trigger parser functionality for trigger subcommand."""

    def test_get_trigger_parser_basic(self):
        """Test basic trigger parser creation."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Test parsing with trigger command and no optional arguments
                args = parser.parse_args(['trigger'])

                assert args.command == 'trigger'
                assert args.rp_url is None
                assert hasattr(args, 'rp_project')
                assert hasattr(args, 'rp_token')


@pytest.mark.unit
class TestArgumentParserIntegration:
    """Integration tests for argument parser."""

    def test_full_workflow_with_auto_analysis(self):
        """Test complete argument parsing workflow with auto-analysis."""
        env_vars = {
            'RP_URL': 'https://prod.reportportal.com',
            'RP_TOKEN': 'prod_api_key',
            'RP_PROJECT': 'prod_project',
            'TRIGGER_AUTO_ANALYSIS': 'false'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Parse arguments with auto-analysis override
                args = parser.parse_args([
                    'write',
                    '--trigger-auto-analysis',
                    '--launch-name', 'Production Test',
                    'production_results.xml'
                ])

                # Verify environment defaults are used
                assert args.rp_url == 'https://prod.reportportal.com'
                assert args.rp_token == 'prod_api_key'
                assert args.rp_project == 'prod_project'

                # Verify CLI arguments override
                assert args.trigger_auto_analysis is True  # CLI overrides env var
                assert args.launch_name == 'Production Test'
                assert args.junits == ['production_results.xml']

    def test_environment_variable_priority(self):
        """Test that environment variables are used as defaults."""
        env_vars = {
            'RP_URL': 'https://env.reportportal.com',
            'RP_TOKEN': 'env_api_key',
            'RP_PROJECT': 'env_project',
            'TRIGGER_AUTO_ANALYSIS': 'true'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Parse with minimal arguments
                args = parser.parse_args(['write', 'test.xml'])

                # Should use environment variable values
                assert args.rp_url == 'https://env.reportportal.com'
                assert args.rp_token == 'env_api_key'
                assert args.rp_project == 'env_project'
                assert args.trigger_auto_analysis is True

    def test_cli_arguments_override_env_vars(self):
        """Test that CLI arguments override environment variables."""
        env_vars = {
            'RP_URL': 'https://env.reportportal.com',
            'RP_TOKEN': 'env_api_key',
            'RP_PROJECT': 'env_project'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Parse with CLI overrides
                args = parser.parse_args([
                    'write',
                    '--rp-url', 'https://cli.reportportal.com',
                    '--rp-token', 'cli_api_key',
                    '--rp-project', 'cli_project',
                    'test.xml'
                ])

                # Should use CLI argument values
                assert args.rp_url == 'https://cli.reportportal.com'
                assert args.rp_token == 'cli_api_key'
                assert args.rp_project == 'cli_project'


@pytest.mark.unit
class TestReleaseParser:
    """Test summary parser functionality (formerly release parser)."""

    def test_get_release_parser_basic(self):
        """Test basic summary parser creation."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Test parsing with minimal required arguments
                args = parser.parse_args(['summary', '--attribute', 'kuadrant:v1.3.1'])

                assert args.command == 'summary'
                assert args.attribute == ['kuadrant:v1.3.1']
                assert args.rp_url is None
                assert args.days == 30  # Default value
                assert args.output_format == 'text'  # Default value
                assert args.show_details is False
                assert args.group_by is None
                assert args.report_title is None

    def test_release_parser_single_attribute(self):
        """Test parser with single attribute."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                args = parser.parse_args(['summary', '--attribute', 'rhcl:1.2.0'])

                assert args.attribute == ['rhcl:1.2.0']

    def test_release_parser_multiple_attributes(self):
        """Test parser with multiple attributes."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                args = parser.parse_args([
                    'summary',
                    '--attribute', 'kuadrant:v1.3.1',
                    '--attribute', 'platform:aws',
                    '--attribute', 'component:gateway'
                ])

                assert len(args.attribute) == 3
                assert 'kuadrant:v1.3.1' in args.attribute
                assert 'platform:aws' in args.attribute
                assert 'component:gateway' in args.attribute

    def test_release_parser_all_options(self):
        """Test parser with all options."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                args = parser.parse_args([
                    '--log-level', 'DEBUG',
                    'summary',
                    '--rp-project', 'test_project',
                    '--rp-url', 'https://test.reportportal.com',
                    '--rp-token', 'test_key',
                    '--attribute', 'kuadrant:v1.3.1',
                    '--attribute', 'platform:aws',
                    '--days', '7',
                    '--output-format', 'json',
                    '--show-details',
                    '--group-by', 'platform',
                    '--report-title', 'Custom Report Title'
                ])

                assert args.rp_project == 'test_project'
                assert args.rp_url == 'https://test.reportportal.com'
                assert args.rp_token == 'test_key'
                assert args.log_level == 'DEBUG'
                assert len(args.attribute) == 2
                assert args.days == 7
                assert args.output_format == 'json'
                assert args.show_details is True
                assert args.group_by == 'platform'
                assert args.report_title == 'Custom Report Title'

    def test_release_parser_output_formats(self):
        """Test parser with different output formats."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Test text format
                args = parser.parse_args(['summary', '--attribute', 'kuadrant:v1.3.1', '--output-format', 'text'])
                assert args.output_format == 'text'

                # Test json format
                args = parser.parse_args(['summary', '--attribute', 'kuadrant:v1.3.1', '--output-format', 'json'])
                assert args.output_format == 'json'

                # Test csv format
                args = parser.parse_args(['summary', '--attribute', 'kuadrant:v1.3.1', '--output-format', 'csv'])
                assert args.output_format == 'csv'

    def test_release_parser_log_levels(self):
        """Test parser with different log levels."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
                    args = parser.parse_args(['--log-level', level, 'summary', '--attribute', 'kuadrant:v1.3.1'])
                    assert args.log_level == level

    def test_release_parser_days_parameter(self):
        """Test parser with different days values."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Test custom days
                args = parser.parse_args(['summary', '--attribute', 'kuadrant:v1.3.1', '--days', '14'])
                assert args.days == 14

                # Test with very large value
                args = parser.parse_args(['summary', '--attribute', 'kuadrant:v1.3.1', '--days', '365'])
                assert args.days == 365

    def test_release_parser_missing_required_attribute(self):
        """Test parser fails without required --attribute."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                # Should raise SystemExit when required argument is missing
                with pytest.raises(SystemExit):
                    parser.parse_args(['summary'])

    def test_release_parser_with_env_vars(self):
        """Test parser uses environment variable defaults."""
        env_vars = {
            'RP_URL': 'https://env.reportportal.com',
            'RP_TOKEN': 'env_api_key',
            'RP_PROJECT': 'env_project'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                args = parser.parse_args(['summary', '--attribute', 'kuadrant:v1.3.1'])

                # Should use environment variable values
                assert args.rp_url == 'https://env.reportportal.com'
                assert args.rp_token == 'env_api_key'
                assert args.rp_project == 'env_project'

    def test_release_parser_cli_overrides_env_vars(self):
        """Test CLI arguments override environment variables."""
        env_vars = {
            'RP_URL': 'https://env.reportportal.com',
            'RP_TOKEN': 'env_api_key',
            'RP_PROJECT': 'env_project'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                args = parser.parse_args([
                    'summary',
                    '--attribute', 'kuadrant:v1.3.1',
                    '--rp-url', 'https://cli.reportportal.com',
                    '--rp-token', 'cli_api_key',
                    '--rp-project', 'cli_project'
                ])

                # Should use CLI argument values
                assert args.rp_url == 'https://cli.reportportal.com'
                assert args.rp_token == 'cli_api_key'
                assert args.rp_project == 'cli_project'


@pytest.mark.unit
class TestReleaseParserIntegration:
    """Integration tests for summary parser (formerly release parser)."""

    def test_kuadrant_release_workflow(self):
        """Test complete workflow for Kuadrant release."""
        env_vars = {
            'RP_URL': 'https://prod.reportportal.com',
            'RP_TOKEN': 'prod_api_key',
            'RP_PROJECT': 'kuadrant_project'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                args = parser.parse_args([
                    'summary',
                    '--attribute', 'kuadrant:v1.3.1',
                    '--attribute', 'platform:aws',
                    '--group-by', 'component',
                    '--show-details',
                    '--days', '14',
                    '--output-format', 'json'
                ])

                # Verify environment defaults are used
                assert args.rp_url == 'https://prod.reportportal.com'
                assert args.rp_token == 'prod_api_key'
                assert args.rp_project == 'kuadrant_project'

                # Verify CLI arguments
                assert args.attribute == ['kuadrant:v1.3.1', 'platform:aws']
                assert args.group_by == 'component'
                assert args.show_details is True
                assert args.days == 14
                assert args.output_format == 'json'

    def test_rhcl_release_workflow(self):
        """Test complete workflow for RHCL release."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                args = parser.parse_args([
                    'summary',
                    '--rp-url', 'https://rhcl.reportportal.com',
                    '--rp-token', 'rhcl_key',
                    '--rp-project', 'rhcl_project',
                    '--attribute', 'rhcl:1.2.0',
                    '--group-by', 'platform',
                    '--report-title', 'RHCL 1.2.0 Release Report',
                    '--output-format', 'text'
                ])

                assert args.rp_url == 'https://rhcl.reportportal.com'
                assert args.rp_token == 'rhcl_key'
                assert args.rp_project == 'rhcl_project'
                assert args.attribute == ['rhcl:1.2.0']
                assert args.group_by == 'platform'
                assert args.report_title == 'RHCL 1.2.0 Release Report'
                assert args.output_format == 'text'

    def test_multi_criteria_filtering(self):
        """Test multi-criteria filtering workflow."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {}
                parser = create_main_parser()

                args = parser.parse_args([
                    'summary',
                    '--attribute', 'kuadrant:v1.3.1',
                    '--attribute', 'platform:gcp',
                    '--attribute', 'component:controller',
                    '--attribute', 'env:staging',
                    '--days', '7'
                ])

                assert len(args.attribute) == 4
                assert 'kuadrant:v1.3.1' in args.attribute
                assert 'platform:gcp' in args.attribute
                assert 'component:controller' in args.attribute
                assert 'env:staging' in args.attribute
                assert args.days == 7


@pytest.mark.unit
class TestLogLevelConfig:
    """Test log level configuration (Issue #6)."""

    def test_log_level_from_config_file(self):
        """Test that log_level from config file is used as default."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                # Simulate config file with DEBUG log level
                mock_load.return_value = {'log_level': 'DEBUG'}
                parser = create_main_parser()

                # Parse without --log-level argument
                args = parser.parse_args(['write', 'test.xml'])

                # Should use config file value
                assert args.log_level == 'DEBUG'

    def test_log_level_cli_overrides_config(self):
        """Test that CLI --log-level overrides config file."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                # Config has DEBUG
                mock_load.return_value = {'log_level': 'DEBUG'}
                parser = create_main_parser()

                # CLI specifies ERROR
                args = parser.parse_args(['--log-level', 'ERROR', 'write', 'test.xml'])

                # Should use CLI value
                assert args.log_level == 'ERROR'

    def test_log_level_default_when_no_config(self):
        """Test that INFO is used when no config is provided."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                # No log_level in config
                mock_load.return_value = {}
                parser = create_main_parser()

                # Parse without --log-level argument
                args = parser.parse_args(['write', 'test.xml'])

                # Should use built-in default (INFO)
                assert args.log_level == 'INFO'

    def test_log_level_works_with_all_commands(self):
        """Test that config log_level works for all commands."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                mock_load.return_value = {'log_level': 'WARNING'}
                parser = create_main_parser()

                # Test write command
                args = parser.parse_args(['write', 'test.xml'])
                assert args.log_level == 'WARNING'

                # Test query command
                args = parser.parse_args(['query'])
                assert args.log_level == 'WARNING'

                # Test trigger command
                args = parser.parse_args(['trigger'])
                assert args.log_level == 'WARNING'

                # Test summary command
                args = parser.parse_args(['summary', '--attribute', 'test:v1'])
                assert args.log_level == 'WARNING'

    def test_log_level_invalid_in_config(self):
        """Test that invalid log level in config raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                # Simulate config file with invalid log level
                mock_load.return_value = {'log_level': 'VERBOSE'}

                # Creating parser should raise ValueError
                with pytest.raises(ValueError) as exc_info:
                    create_main_parser()

                # Check error message contains the invalid value
                error_msg = str(exc_info.value)
                assert 'Invalid log level in config' in error_msg
                assert 'VERBOSE' in error_msg
                assert 'Must be one of' in error_msg

    def test_log_level_invalid_in_config_case_insensitive(self):
        """Test that invalid log level works with case normalization."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                # Lowercase 'trace' should also be rejected
                mock_load.return_value = {'log_level': 'trace'}

                with pytest.raises(ValueError) as exc_info:
                    create_main_parser()

                error_msg = str(exc_info.value)
                assert 'Invalid log level in config' in error_msg
                # Should show uppercase version in error
                assert 'TRACE' in error_msg

    def test_no_premature_debug_messages_during_config_load(self):
        """Test that debug messages during config loading are suppressed until log level is set."""
        import io
        from unittest.mock import patch
        from reportportal.rp_dispatcher import main

        # Capture stderr to check for debug messages
        captured_stderr = io.StringIO()

        with patch.dict(os.environ, {}, clear=True):
            with patch('reportportal.config.load_config_file') as mock_load:
                # Simulate config file exists and has values
                mock_load.return_value = {'log_level': 'INFO', 'rp_url': 'http://test.com'}

                # Redirect stderr
                with patch('sys.stderr', captured_stderr):
                    try:
                        # Run with INFO level (default from config)
                        # This will fail because we don't have valid args, but we just want to check logging
                        main(['write', 'test.xml'])
                    except SystemExit:
                        pass

                # Check that no "Loaded config from" or "Config file" debug messages appear
                stderr_output = captured_stderr.getvalue()
                assert "Loaded config from" not in stderr_output, \
                    "Debug message 'Loaded config from' should not appear with INFO log level"
                assert "Config file not found" not in stderr_output, \
                    "Debug message 'Config file not found' should not appear with INFO log level"
