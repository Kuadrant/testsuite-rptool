"""
Unit tests for configuration file handling.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from reportportal.config import (
    get_config_file_path,
    load_config_file,
    get_config_defaults,
    merge_with_env_vars,
    get_effective_defaults,
)


class TestConfigFilePath:
    """Test configuration file path resolution."""

    def test_get_config_file_path_with_platformdirs(self):
        """Test that config file path is returned when platformdirs is available."""
        path = get_config_file_path()
        assert path is not None
        assert isinstance(path, Path)
        assert path.name == "settings.yaml"
        assert "rptool" in str(path)


class TestLoadConfigFile:
    """Test YAML config file loading."""

    def test_load_config_file_not_exists(self):
        """Test loading when config file doesn't exist."""
        with patch("reportportal.config.get_config_file_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/settings.yaml")
            config = load_config_file()
            assert config == {}

    def test_load_config_file_empty(self):
        """Test loading empty config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with patch("reportportal.config.get_config_file_path") as mock_path:
                mock_path.return_value = Path(temp_path)
                config = load_config_file()
                assert config == {}
        finally:
            os.unlink(temp_path)

    def test_load_config_file_valid(self):
        """Test loading valid config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
rp_url: "https://test.com"
rp_project: "test_project"
rp_token: "test_token"
trigger_auto_analysis: true
launch_name: "Test Launch"
launch_description: "Test Description"
log_level: "DEBUG"
"""
            )
            temp_path = f.name

        try:
            with patch("reportportal.config.get_config_file_path") as mock_path:
                mock_path.return_value = Path(temp_path)
                config = load_config_file()
                assert config["rp_url"] == "https://test.com"
                assert config["rp_project"] == "test_project"
                assert config["rp_token"] == "test_token"
                assert config["trigger_auto_analysis"] is True
                assert config["launch_name"] == "Test Launch"
                assert config["launch_description"] == "Test Description"
                assert config["log_level"] == "DEBUG"
        finally:
            os.unlink(temp_path)

    def test_load_config_file_invalid_yaml(self):
        """Test loading invalid YAML file raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:")
            temp_path = f.name

        try:
            with patch("reportportal.config.get_config_file_path") as mock_path:
                mock_path.return_value = Path(temp_path)
                # Should raise ValueError on error
                with pytest.raises(ValueError) as exc_info:
                    load_config_file()

                # Check error message contains file path
                error_msg = str(exc_info.value)
                assert "Error reading config file" in error_msg
        finally:
            os.unlink(temp_path)


class TestGetConfigDefaults:
    """Test getting config defaults from file."""

    def test_get_config_defaults_builtin(self):
        """Test that built-in defaults are returned when no config file exists."""
        with patch("reportportal.config.load_config_file") as mock_load:
            mock_load.return_value = {}
            defaults = get_config_defaults()

            assert defaults["rp_url"] is None
            assert defaults["rp_project"] is None
            assert defaults["rp_token"] is None
            assert defaults["trigger_auto_analysis"] is False
            assert defaults["launch_name"] is None
            assert defaults["launch_description"] == ""
            assert defaults["log_level"] == "INFO"

    def test_get_config_defaults_from_file(self):
        """Test that config file values override built-in defaults."""
        with patch("reportportal.config.load_config_file") as mock_load:
            mock_load.return_value = {
                "rp_url": "https://config-file.com",
                "rp_project": "file_project",
                "trigger_auto_analysis": True,
                "launch_name": "Test Launch",
                "launch_description": "Test Description",
                "log_level": "DEBUG",
            }
            defaults = get_config_defaults()

            assert defaults["rp_url"] == "https://config-file.com"
            assert defaults["rp_project"] == "file_project"
            assert defaults["rp_token"] is None  # Not in config
            assert defaults["trigger_auto_analysis"] is True
            assert defaults["launch_name"] == "Test Launch"
            assert defaults["launch_description"] == "Test Description"
            assert defaults["log_level"] == "DEBUG"


class TestMergeWithEnvVars:
    """Test merging config with environment variables."""

    def test_merge_with_env_vars_empty_env(self):
        """Test that config defaults are returned when no env vars are set."""
        config = {
            "rp_url": "https://config.com",
            "rp_project": "config_project",
            "rp_token": "config_token",
            "trigger_auto_analysis": False,
            "launch_name": None,
            "launch_description": "",
            "log_level": "INFO",
        }

        with patch.dict(os.environ, {}, clear=True):
            merged = merge_with_env_vars(config)
            assert merged == config

    def test_merge_with_env_vars_override(self):
        """Test that env vars override config values."""
        config = {
            "rp_url": "https://config.com",
            "rp_project": "config_project",
            "rp_token": "config_token",
            "trigger_auto_analysis": False,
            "launch_name": "Config Launch",
            "launch_description": "Config Description",
            "log_level": "INFO",
        }

        env_vars = {
            "RP_URL": "https://env.com",
            "RP_PROJECT": "env_project",
            "TRIGGER_AUTO_ANALYSIS": "true",
            "RP_LAUNCH_NAME": "Env Launch",
            "RP_LAUNCH_DESCRIPTION": "Env Description",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            merged = merge_with_env_vars(config)
            assert merged["rp_url"] == "https://env.com"
            assert merged["rp_project"] == "env_project"
            assert merged["rp_token"] == "config_token"  # Not overridden
            assert merged["trigger_auto_analysis"] is True
            assert merged["launch_name"] == "Env Launch"
            assert merged["launch_description"] == "Env Description"
            assert merged["log_level"] == "DEBUG"


class TestTriggerAutoAnalysisConversion:
    """Test boolean conversion for TRIGGER_AUTO_ANALYSIS."""

    def test_trigger_auto_analysis_true_values(self):
        """Test that various true string values are converted to boolean True."""
        config = {
            "rp_url": None,
            "rp_project": None,
            "rp_token": None,
            "trigger_auto_analysis": False,
            "launch_name": None,
            "launch_description": "",
            "log_level": "INFO",
        }

        true_values = ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]

        for val in true_values:
            with patch.dict(os.environ, {"TRIGGER_AUTO_ANALYSIS": val}, clear=True):
                merged = merge_with_env_vars(config)
                assert (
                    merged["trigger_auto_analysis"] is True
                ), f"Failed for value: {val}"

    def test_trigger_auto_analysis_false_values(self):
        """Test that various false string values are converted to boolean False."""
        config = {
            "rp_url": None,
            "rp_project": None,
            "rp_token": None,
            "trigger_auto_analysis": True,
            "launch_name": None,
            "launch_description": "",
            "log_level": "INFO",
        }

        false_values = ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF"]

        for val in false_values:
            with patch.dict(os.environ, {"TRIGGER_AUTO_ANALYSIS": val}, clear=True):
                merged = merge_with_env_vars(config)
                assert (
                    merged["trigger_auto_analysis"] is False
                ), f"Failed for value: {val}"

    def test_trigger_auto_analysis_no_env(self):
        """Test that config value is preserved when env var is not set."""
        config = {
            "rp_url": None,
            "rp_project": None,
            "rp_token": None,
            "trigger_auto_analysis": True,
            "launch_name": None,
            "launch_description": "",
            "log_level": "INFO",
        }

        with patch.dict(os.environ, {}, clear=True):
            merged = merge_with_env_vars(config)
            assert merged["trigger_auto_analysis"] is True


class TestGetEffectiveDefaults:
    """Test getting effective defaults with full priority chain."""

    def test_get_effective_defaults_priority(self):
        """Test that full priority chain works correctly."""
        # Mock config file
        with patch("reportportal.config.load_config_file") as mock_load:
            mock_load.return_value = {
                "rp_url": "https://config.com",
                "rp_project": "config_project",
                "trigger_auto_analysis": False,
                "launch_name": "Config Launch",
                "log_level": "INFO",
            }

            # Set env vars
            env_vars = {
                "RP_URL": "https://env.com",
                "TRIGGER_AUTO_ANALYSIS": "1",
                "RP_LAUNCH_DESCRIPTION": "Env Description",
                "LOG_LEVEL": "DEBUG",
            }

            with patch.dict(os.environ, env_vars, clear=True):
                defaults = get_effective_defaults()

                # ENV overrides config
                assert defaults["rp_url"] == "https://env.com"
                assert defaults["trigger_auto_analysis"] is True
                assert defaults["launch_description"] == "Env Description"
                assert defaults["log_level"] == "DEBUG"

                # Config used when no ENV
                assert defaults["rp_project"] == "config_project"
                assert defaults["launch_name"] == "Config Launch"

                # Built-in default when neither config nor ENV
                assert defaults["rp_token"] is None

