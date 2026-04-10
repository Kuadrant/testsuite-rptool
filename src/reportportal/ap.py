import argparse
from importlib.metadata import version, PackageNotFoundError
from reportportal.config import get_effective_defaults


def _get_config_defaults() -> dict:
    """
    Get configuration defaults with full priority chain:
    built-in defaults < config file < environment variables.

    CLI arguments will override these values.
    """
    # Get all config from config file + env vars
    core_config = get_effective_defaults()

    return {
        "rp_url": core_config["rp_url"],
        "rp_token": core_config["rp_token"],
        "rp_project": core_config["rp_project"],
        "rp_launch_name": core_config["launch_name"],
        # The empty string is necessary to enable additional description to be added on .finish_launch()
        "rp_launch_description": core_config["launch_description"],
        "trigger_auto_analysis": core_config["trigger_auto_analysis"],
        "log_level": core_config["log_level"],
    }


def _validate_rp_options(options: argparse.Namespace, parser: argparse.ArgumentParser) -> bool:
    """Validate that required ReportPortal options are provided."""
    if not all([options.rp_url, options.rp_project, options.rp_token]):
        parser.error(
            "RP_URL, PR_PROJECT, and RP_TOKEN must be specified via environment variables or arguments"
        )

def create_main_parser() -> argparse.ArgumentParser:
    """
    Create the main argument parser with subcommands.

    Returns:
        ArgumentParser with subcommands configured
    """
    # Get version from package metadata (set by setuptools-scm)
    try:
        pkg_version = version('rptool')
    except PackageNotFoundError:
        pkg_version = 'unknown (not installed)'

    # Get configuration defaults (config file + env vars + built-in defaults)
    # Must be loaded before creating arguments that use these defaults
    defaults = _get_config_defaults()

    parser = argparse.ArgumentParser(
        prog='rptool',
        description='Unified command-line interface for ReportPortal tools',
        epilog='Use "rptool <command> --help" for more information about a command.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'rptool {pkg_version}'
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=defaults["log_level"],
        help="Set the logging level (default: from config or INFO)"
    )

    # Create subparsers for each command
    subparsers = parser.add_subparsers(
        title='Available commands',
        description='ReportPortal operations',
        dest='command',
        metavar='<command>',
        required=True
    )

    # Adding subparsers' arguments
    subparsers_hanlers = [
        _add_write_arguments,
        _add_query_arguments,
        _add_trigger_arguments,
        _add_summary_arguments,
        _add_completion_arguments,
    ]

    for _add_handler in subparsers_hanlers:
        _add_handler(subparsers, defaults)

    return parser



def _add_common_rp_args(parser: argparse.ArgumentParser, defaults: dict) -> None:
    """Add common ReportPortal arguments to parser."""
    parser.add_argument(
        "--rp-project",
        help="RP project, will override env variable",
        default=defaults["rp_project"],
    )
    parser.add_argument(
        "--rp-url",
        help="RP URL, will override env variable",
        default=defaults["rp_url"],
    )
    parser.add_argument(
        "--rp-token",
        help="RP API token, will override env variable",
        default=defaults["rp_token"],
    )



def _add_write_arguments(subparsers: argparse.ArgumentParser, defaults: dict) -> None:
    """Add arguments for write command."""
    parser = subparsers.add_parser(
        'write',
        help='Import JUnit XML results to ReportPortal',
        description='Import JUnit XML test results to ReportPortal with property preservation',
        epilog='The Spice must flow'
    )
    _add_common_rp_args(parser, defaults)

    parser.add_argument(
        "--launch-name", 
        help="Override Launch name that will be reported, otherwise filename will be used",
        default=defaults['rp_launch_name']
    )
    parser.add_argument(
        "--launch-description", 
        help="Custom head section to launch description, passthrough description will be added from the junit if available",
        # The empty string from defaults is necessary to enable additional description to be added on .finish_launch() 
        default=defaults['rp_launch_description'],
    )
    parser.add_argument(
        "--trigger-auto-analysis",
        action="store_true",
        help="Enable auto-analysis properties for ReportPortal launches (can also be set via TRIGGER_AUTO_ANALYSIS env var)",
        default=defaults['trigger_auto_analysis']
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate ReportPortal API calls without actually sending data",
        default=False
    )
    parser.add_argument("junits", nargs='+', help="path to all junit results, multiple files will be reportes as one launch")
    

def _add_query_arguments(subparsers: argparse.ArgumentParser, defaults: dict) -> None:
    """Add arguments for query command."""

    parser = subparsers.add_parser(
        'query',
        help='Query ReportPortal launches and test items',
        description='Query tool for ReportPortal to list launches and other information',
        epilog='Query the portal'
    )

    _add_common_rp_args(parser, defaults)


    parser.add_argument(
        "--launch-id",
        help="Launch ID to query test items for (if not specified, will list all launches)",
        default=None
    )
    parser.add_argument(
        "--launch-name",
        help="Launch name to query test items for (uses the most recent launch with this name). "
             "Append ' #N' to select a specific launch number (e.g. 'my-launch #3')",
        default=None
    )
    parser.add_argument(
        "--status",
        choices=["PASSED", "FAILED", "SKIPPED", "INTERRUPTED", "IN_PROGRESS"],
        help="Filter test items by status (only applies when --launch-id is specified)",
        default=None
    )
    parser.add_argument(
        "--name",
        help="Filter test items by name (partial match, only applies when --launch-id is specified)",
        default=None
    )
    parser.add_argument(
        "--name-regex",
        help="Filter test items by name using regex (local filtering, only applies when --launch-id is specified)",
        default=None
    )
    parser.add_argument(
        "--attribute",
        action="append",
        help="Filter launches or test items by attribute (local filtering). "
             "Format: 'key:value' to match both key and value, or 'value' to match value only. "
             "Can be specified multiple times.",
        default=None
    )
    parser.add_argument(
        "--attribute-regex",
        action="append",
        help="Filter launches or test items by attribute using regex (local filtering). "
             "Format: 'key:pattern' to match key exactly and value with regex, or 'pattern' to match value with regex. "
             "Can be specified multiple times.",
        default=None
    )
    parser.add_argument(
        "--show-attributes",
        action="store_true",
        help="Display attributes in the output table",
        default=False
    )
    parser.add_argument(
        "--names-only",
        action="store_true",
        help="Output only test case names for STEP items (one per line, no formatting, excludes SUITE items). Only applies when --launch-id is specified.",
        default=False
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,  # This is the CLI default, actual defaults differ by query type
        help="Maximum number of items to fetch from API. Default: 24 for launches, unlimited for test items. Use 0 for unlimited."
    )


def _add_trigger_arguments(subparsers: argparse.ArgumentParser, defaults: dict) -> None:
    """Add arguments for trigger command."""
    parser = subparsers.add_parser(
        'trigger',
        help='Trigger auto-analysis on launches',
        description='Trigger auto-analysis on launches that have items to investigate',
        epilog='Trigger happy'
    )
    _add_common_rp_args(parser, defaults)


def _add_summary_arguments(subparsers: argparse.ArgumentParser, defaults: dict) -> None:
    """Add arguments for summary command."""

    parser = subparsers.add_parser(
        'summary',
        help='Generate release testing summary',
        description='Generate comprehensive release testing summary based on launch attributes',
        epilog='Release report generator'
    )

    _add_common_rp_args(parser, defaults)

    parser.add_argument(
        "--attribute",
        action="append",
        required=True,
        help="Filter launches by attribute. Format: 'key:value' (e.g., 'kuadrant:v1.3.1', 'rhcl:1.2.0'). "
             "Can be specified multiple times to filter by multiple attributes (AND logic)."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back for launches (default: 30)"
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--show-details",
        action="store_true",
        help="Show detailed breakdown by launch",
        default=False
    )
    parser.add_argument(
        "--group-by",
        help="Group results by specific attribute key (e.g., 'platform', 'component', 'build')"
    )
    parser.add_argument(
        "--report-title",
        help="Custom title for the report (default: derived from attributes)"
    )


def _add_completion_arguments(subparsers: argparse.ArgumentParser, _) -> None:
    """Add arguments for completion command."""

    parser = subparsers.add_parser(
        'completion',
        help='Generate shell completion script',
        description='Generate shell completion script for rptool command',
        epilog='Example: rptool completion bash > /etc/bash_completion.d/rptool'
    )

    parser.add_argument(
        "shell",
        choices=["bash", "zsh"],
        help="Shell type for which to generate completion script"
    )

