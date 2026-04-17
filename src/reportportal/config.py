"""
Configuration file handling for rptool.

Supports loading configuration from YAML files with the following priority:
1. CLI arguments (handled by argparse)
2. Environment variables
3. Config file (~/.config/rptool/settings.yaml or platform equivalent)
4. Built-in defaults
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
from platformdirs import user_config_dir

import yaml


def get_config_file_path() -> Optional[Path]:
    """
    Get the path to the user's configuration file.

    Returns:
        Path to config file if platformdirs is available, None otherwise
    """

    config_dir = Path(user_config_dir("rptool", appauthor=False))
    config_file = config_dir / "settings.yaml"

    return config_file


def load_config_file() -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Returns:
        Dictionary with configuration values, empty dict if file doesn't exist
        or is empty.

    Raises:
        ValueError: When config file cannot be parsed properly.
    """

    config_file = get_config_file_path()

    if not config_file.exists():
        logger.debug("No config file present, using defaults")
        return {}

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            if config is None:
                logger.debug("Config file empty")
                return {}
            logger.info("Config file loaded successfully")
            return config
    except Exception as e:
        # need to raise ValueError to indicate critical problem
        raise ValueError(f"Error reading config file {config_file} {e}")


def get_config_defaults() -> Dict[str, Any]:
    """
    Get configuration values with priority: config file > built-in defaults.

    Returns:
        Dictionary with configuration defaults
    """
    # Built-in defaults
    defaults = {
        "rp_url": None,
        "rp_token": None,
        "rp_project": None,
        "trigger_auto_analysis": False,
        "launch_name": None,
        "launch_description": "",
        "log_level": "INFO",
        "requests_ca_bundle": None,
    }

    # Load from config file
    config = load_config_file()

    # Override with config file values
    if config:
        if config.get("rp_url"):
            defaults["rp_url"] = config["rp_url"]
        if config.get("rp_project"):
            defaults["rp_project"] = config["rp_project"]
        if config.get("rp_token"):
            defaults["rp_token"] = config["rp_token"]
        if config.get("trigger_auto_analysis") is not None:
            defaults["trigger_auto_analysis"] = config["trigger_auto_analysis"]
        if config.get("launch_name"):
            defaults["launch_name"] = config["launch_name"]
        if config.get("launch_description") is not None:
            defaults["launch_description"] = config["launch_description"]
        if config.get("log_level"):
            defaults["log_level"] = config["log_level"]
        if config.get("requests_ca_bundle"):
            defaults["requests_ca_bundle"] = config["requests_ca_bundle"]

    return defaults


def merge_with_env_vars(config_defaults: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge config file defaults with environment variables.

    Environment variables take precedence over config file values.

    Args:
        config_defaults: Dictionary with config file defaults

    Returns:
        Dictionary with merged values
    """
    merged = config_defaults.copy()

    # Environment variables override config file
    if os.environ.get("RP_URL"):
        merged["rp_url"] = os.environ.get("RP_URL")
    if os.environ.get("RP_TOKEN"):
        merged["rp_token"] = os.environ.get("RP_TOKEN")
    if os.environ.get("RP_PROJECT"):
        merged["rp_project"] = os.environ.get("RP_PROJECT")
    if os.environ.get("RP_LAUNCH_NAME"):
        merged["launch_name"] = os.environ.get("RP_LAUNCH_NAME")
    if os.environ.get("RP_LAUNCH_DESCRIPTION"):
        merged["launch_description"] = os.environ.get("RP_LAUNCH_DESCRIPTION")
    if os.environ.get("LOG_LEVEL"):
        merged["log_level"] = os.environ.get("LOG_LEVEL")
    if os.environ.get("REQUESTS_CA_BUNDLE"):
        merged["requests_ca_bundle"] = os.environ.get("REQUESTS_CA_BUNDLE")

    # Convert string environment variable to boolean for trigger_auto_analysis
    trigger_auto_analysis_env = os.environ.get("TRIGGER_AUTO_ANALYSIS", "").lower()
    if trigger_auto_analysis_env in ("true", "1", "yes", "on"):
        merged["trigger_auto_analysis"] = True
    elif trigger_auto_analysis_env in ("false", "0", "no", "off"):
        merged["trigger_auto_analysis"] = False

    return merged


def get_effective_defaults() -> Dict[str, Any]:
    """
    Get effective configuration defaults with full priority chain:
    built-in defaults < config file < environment variables.

    Note: CLI arguments will override these in argparse.

    Also handles injecting REQUESTS_CA_BUNDLE into environment if configured
    but not already set.

    Returns:
        Dictionary with effective default values
    """
    config_defaults = get_config_defaults()
    merged = merge_with_env_vars(config_defaults)

    # Inject REQUESTS_CA_BUNDLE into environment if configured but not already set
    if merged.get("requests_ca_bundle") and not os.environ.get("REQUESTS_CA_BUNDLE"):
        os.environ["REQUESTS_CA_BUNDLE"] = merged["requests_ca_bundle"]
        logger.debug("Set REQUESTS_CA_BUNDLE from config: {}", merged['requests_ca_bundle'])

    return merged

