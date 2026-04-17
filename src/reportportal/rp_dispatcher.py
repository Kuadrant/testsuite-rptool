"""
ReportPortal Tool - Unified Command Dispatcher

This module provides a unified command-line interface for all ReportPortal tools.
"""

import sys
import argparse
from typing import List, Optional
import os

from loguru import logger

try:
    import shtab
    SHTAB_AVAILABLE = True
except ImportError:
    SHTAB_AVAILABLE = False

from . import ap
from .writer import RPWriter
from .rp_query import run_query
from .rp_trigger import run_auto_trigger
from .rp_release import run_release_summary



def _generate_bash_completion() -> str:
    """Generate bash completion script for rptool using shtab."""
    if not SHTAB_AVAILABLE:
        raise ImportError("shtab is not installed. Install it with: pip install shtab")

    parser = ap.create_main_parser()
    return shtab.complete(parser, shell='bash')


def _generate_zsh_completion() -> str:
    """Generate zsh completion script for rptool using shtab."""
    if not SHTAB_AVAILABLE:
        raise ImportError("shtab is not installed. Install it with: pip install shtab")

    parser = ap.create_main_parser()
    return shtab.complete(parser, shell='zsh')


def run_completion_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """
    Execute the completion command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not SHTAB_AVAILABLE:
        print("Error: shtab is not installed.", file=sys.stderr)
        print("Install it with: pip install shtab", file=sys.stderr)
        print("Or: uv pip install shtab", file=sys.stderr)
        return 1

    try:
        if args.shell == "bash":
            print(_generate_bash_completion())
        elif args.shell == "zsh":
            print(_generate_zsh_completion())
        else:
            logger.error(f"Unsupported shell type: {args.shell}")
            return 1
        return 0
    except Exception as e:
        logger.exception(e)
        logger.error(f"Error generating completion: {e}")
        return 1


def run_write_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """
    Execute the write command (rp_writer).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    ap._validate_rp_options(args, parser)

    try:
        logger.info("Starting ReportPortal JUnit writer")

        # Validate JUnit file
        if not args.junits:
            logger.error('JUnit file path is required')
            return 1

        logger.debug(f"ReportPortal URL: {args.rp_url}")
        logger.debug(f"ReportPortal project: {args.rp_project}")
        logger.debug(f"JUnit files: {args.junits}")

        # Create writer and process file
        writer = RPWriter(args)
        return writer.process_junit_file()
    except Exception as e:
        logger.exception(f"Error: {e}", file=sys.stderr)
        return 1


def run_query_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """
    Execute the query command (rp_query).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    ap._validate_rp_options(args, parser)

    return run_query(args)


def run_trigger_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """
    Execute the trigger command (rp_trigger).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Validate required fields
    ap._validate_rp_options(args, parser)

    return run_auto_trigger(args)


def run_summary_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """
    Execute the summary command (rp_release).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Validate required fields
    ap._validate_rp_options(args, parser)


    return run_release_summary(args)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the rptool dispatcher.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Remove default loguru handler immediately to prevent premature debug messages
    # (e.g., during config file loading before log level is determined)
    logger.remove()
    # Setup intermittent WARNING logger for any configuration logs
    # or set to environmnet variable LOG_LEVEL if defined
    logger.add(sink=sys.stderr, level=os.environ.get('LOG_LEVEL', "").upper() or 'WARNING')

    try:
        parser = ap.create_main_parser()
    except ValueError as e:
        logger.error('Improper configuration {}', str(e))
        return 1


    # Parse arguments
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if e.code is not None else 1

    # Setup logging handler with configured log level
    logger.remove()
    logger.add(sink=sys.stderr, level=args.log_level)

    # Dispatch to appropriate command handler
    command_handlers = {
        'write': run_write_command,
        'query': run_query_command,
        'trigger': run_trigger_command,
        'summary': run_summary_command,
        'completion': run_completion_command,
    }

    handler = command_handlers.get(args.command)
    if handler:
        return handler(args, parser)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
