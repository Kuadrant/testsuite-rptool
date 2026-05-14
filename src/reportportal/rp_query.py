"""
ReportPortal Query Tool - Core Implementation

This module handles querying ReportPortal for launch information.
"""

from typing import List, Dict, Optional, Any
from loguru import logger
from tabulate import tabulate
from argparse import Namespace

from .rp_api_client import ReportPortalAPIClient
from . import rp_query_utils as utils
from .junit_parser import timestamp_rp_to_junit


# Default limits for API queries
DEFAULT_LAUNCHES_LIMIT = 24  # Show recent launches by default
DEFAULT_TEST_ITEMS_LIMIT = 0  # Show all test items by default (0 = unlimited)


# =============================================================================
# API Communication Wrappers
# =============================================================================

def fetch_launches(client: ReportPortalAPIClient, limit: Optional[int] = None) -> Optional[List[Dict]]:
    """
    Get launches from ReportPortal project, sorted by start time (most recent first).

    Args:
        client: ReportPortal API client instance
        limit: Maximum number of launches to fetch (None uses default, 0 for API limit of 1000)

    Returns:
        List of launch dictionaries or None if request failed
    """
    try:
        # Use default if not specified
        if limit is None:
            limit = DEFAULT_LAUNCHES_LIMIT

        # Use limit as page_size for API call (0 means use API default)
        page_size = limit if limit > 0 else 1000
        return client.get_launches(sort_by='startTime,DESC', page_size=page_size)
    except Exception as e:
        logger.error(f"Failed to fetch launches: {e}")
        return None


def fetch_launch_by_name(client: ReportPortalAPIClient, launch_name: str) -> Optional[Dict]:
    """
    Find a launch by name, optionally with a launch number.

    Supports formats:
        "launch-name"      -> most recent launch with that name
        "launch-name #3"   -> launch with that name and number 3

    Args:
        client: ReportPortal API client instance
        launch_name: Launch name, optionally followed by " #N"

    Returns:
        Launch dictionary or None if not found
    """
    try:
        import re
        match = re.match(r'^(.+?)\s*#(\d+)$', launch_name)
        if match:
            name = match.group(1)
            number = int(match.group(2))
            filters = {'filter.eq.name': name, 'filter.eq.number': number}
        else:
            name = launch_name
            filters = {'filter.eq.name': name}

        launches = client.get_launches(sort_by='startTime,DESC', page_size=1, filters=filters)
        if launches:
            launch = launches[0]
            logger.info(f"Found launch '{launch_name}' with ID: {launch.get('id')}")
            return launch
        else:
            logger.error(f"No launch found with name: {launch_name}")
            return None
    except Exception as e:
        logger.error(f"Failed to search for launch by name: {e}")
        return None


def fetch_test_items(launch_id: str, client: ReportPortalAPIClient, options: Namespace, limit: Optional[int] = None) -> Optional[List[Dict]]:
    """
    Get test items for a specific launch from ReportPortal.

    Args:
        launch_id: The launch ID to query
        client: ReportPortal API client instance
        options: Parsed command line options
        limit: Maximum number of test items to fetch (None uses default, 0 for API limit of 1000)

    Returns:
        List of test item dictionaries or None if request failed
    """
    # Build API-level filters
    filters = ReportPortalAPIClient.build_filter_dict(
        status=getattr(options, 'status', None),
        name_contains=getattr(options, 'name', None)
    )

    # Log applied filters
    if filters:
        if 'filter.eq.status' in filters:
            logger.debug(f"Filtering by status: {filters['filter.eq.status']}")
        if 'filter.cnt.name' in filters:
            logger.debug(f"Filtering by name containing: {filters['filter.cnt.name']}")

    try:
        # Use default if not specified
        if limit is None:
            limit = DEFAULT_TEST_ITEMS_LIMIT

        # Use limit as page_size for API call (0 means use API default)
        page_size = limit if limit > 0 else 1000
        return client.get_test_items(launch_id, page_size=page_size, filters=filters if filters else None)
    except Exception as e:
        logger.error(f"Failed to fetch test items: {e}")
        return None


# =============================================================================
# Filtering Logic (using reusable utilities)
# =============================================================================

def apply_all_filters(items: List[Dict],
                     name_regex: Optional[str],
                     attribute_filters: Optional[List[str]],
                     attribute_regex_filters: Optional[List[str]]) -> Optional[List[Dict]]:
    """
    Apply all local filters to items/launches.

    Returns:
        Filtered items or None if regex error occurred
    """
    original_count = len(items)

    # Apply filters using reusable utilities
    try:
        result = utils.apply_filters(
            items,
            name_regex=name_regex,
            attribute_filters=attribute_filters,
            attribute_regex_filters=attribute_regex_filters
        )

        # Log filter results
        if name_regex and len(result) < original_count:
            logger.debug(f"Name regex filter reduced items from {original_count} to {len(result)}")
            original_count = len(result)

        if attribute_filters and len(result) < original_count:
            logger.debug(f"Attribute filter(s) reduced items from {original_count} to {len(result)}")
            original_count = len(result)

        if attribute_regex_filters and len(result) < original_count:
            logger.debug(f"Attribute regex filter(s) reduced items from {original_count} to {len(result)}")

        return result

    except Exception as e:
        logger.error(f"Filter error: {e}")
        return None


# =============================================================================
# Formatting and Display (using reusable utilities)
# =============================================================================


def _format_timestamp(timestamp_ms: Optional[int]) -> str:
    """
    Format ReportPortal timestamp (milliseconds) to readable datetime.

    Args:
        timestamp_ms: Unix timestamp in milliseconds

    Returns:
        Formatted datetime string (YYYY-MM-DD HH:MM)
    """
    if not timestamp_ms:
        return 'N/A'

    try:
        # Reuse existing timestamp conversion
        iso_time = timestamp_rp_to_junit(timestamp_ms)
        # Extract date and time part (YYYY-MM-DD HH:MM) from ISO format
        # ISO format is like: 2024-03-19T14:30:00+00:00
        return iso_time[:16].replace('T', ' ')
    except Exception:
        return 'N/A'


def _build_launch_row(launch: Dict, show_attributes: bool) -> List[Any]:
    """Build a table row for a launch."""
    launch_id = launch.get('id', 'N/A')
    launch_name = launch.get('name', 'N/A')
    launch_number = launch.get('number', 'N/A')
    start_time = launch.get('startTime')

    # Extract statistics using utility function
    stats = utils.extract_launch_statistics(launch)

    # Shorten ID for display
    short_id = launch_id[:8] if len(str(launch_id)) > 8 else launch_id

    row = [
        short_id,
        launch_name,
        launch_number,
        _format_timestamp(start_time),
        stats['total'],
        stats['passed'],
        stats['failed'],
        stats['skipped'],
        stats['to_investigate'],
        stats['product_bug'],
        stats['automation_bug'],
        stats['system_issue'],
    ]

    if show_attributes:
        row.append(utils.format_attributes(launch.get('attributes', [])))

    return row


def _build_test_item_row(item: Dict, suite_name: str, show_attributes: bool) -> List[Any]:
    """Build a table row for a test item."""
    item_name = item.get('name', 'N/A')
    status = item.get('status', 'N/A')

    # Get duration using utility function
    duration_sec = utils.extract_item_duration(item)

    # Format defect using utility function
    issue = item.get('issue', {})
    issue_type = issue.get('issueType', 'N/A') if issue else '-'
    defect_short = utils.format_defect_type(issue_type)

    row = [
        suite_name,
        item_name,
        status,
        utils.format_duration(duration_sec),
        defect_short,
    ]

    if show_attributes:
        row.append(utils.format_attributes(item.get('attributes', [])))

    return row


def _output_names_only(items: List[Dict]) -> None:
    """Output only STEP item names (one per line)."""
    step_items = utils.exclude_type(items, utils.ITEM_TYPE_SUITE)
    names = utils.extract_names(step_items)
    for name in names:
        print(name)


def _output_launches_table(launches: List[Dict], show_attributes: bool) -> None:
    """
    Output launches in table format.

    Args:
        launches: List of launch dictionaries
        show_attributes: Whether to display attributes column
    """
    logger.info(f"Found {len(launches)} launches:\n")

    # Print column abbreviations legend
    print("Column abbreviations:")
    print("  # = Launch Number")
    print("  TI = To Investigate, PB = Product Bug, AB = Automation Bug, SI = System Issue")
    print()

    headers = ["ID", "Name", "#", "Start Time", "Total", "Pass", "Fail", "Skip", "TI", "PB", "AB", "SI"]
    if show_attributes:
        headers.append("Attributes")

    table_data = []
    for launch in launches:
        try:
            table_data.append(_build_launch_row(launch, show_attributes))
        except Exception as e:
            logger.error(f"Error processing launch: {e}")

    print(tabulate(table_data, headers=headers, tablefmt="simple"))


def _output_launch_header(launch: Dict, show_attributes: bool) -> None:
    """
    Output launch information header.

    Args:
        launch: Launch dictionary
        show_attributes: Whether to display attributes
    """
    launch_name = launch.get('name', 'N/A')
    launch_number = launch.get('number', 'N/A')
    start_time = launch.get('startTime')

    # Extract statistics
    stats = utils.extract_launch_statistics(launch)

    print("=" * 80)
    print(f"Launch: {launch_name} (#{launch_number})")
    print(f"Started: {_format_timestamp(start_time)}")

    # Results tally
    print(f"\nResults: Total={stats['total']}, Pass={stats['passed']}, "
          f"Fail={stats['failed']}, Skip={stats['skipped']}")
    print(f"Defects: TI={stats['to_investigate']}, PB={stats['product_bug']}, "
          f"AB={stats['automation_bug']}, SI={stats['system_issue']}")

    # Attributes
    if show_attributes:
        attrs_str = utils.format_attributes(launch.get('attributes', []))
        print(f"Attributes: {attrs_str}")

    print("=" * 80)
    print()


def _output_test_items_table(items: List[Dict], show_attributes: bool) -> None:
    """Output test items in table format."""
    headers = ["Suite", "Name", "Status", "Duration", "Defect"]
    if show_attributes:
        headers.append("Attributes")

    table_data = []
    current_suite = '-'

    # Iterate through all items to track suite context
    for item in items:
        item_type = item.get('type', '')

        # Track suite/test name for context
        if item_type in (utils.ITEM_TYPE_SUITE, utils.ITEM_TYPE_TEST):
            current_suite = item.get('name', '-')
        # Only display STEP items (actual test cases)
        elif item_type == utils.ITEM_TYPE_STEP:
            try:
                table_data.append(_build_test_item_row(item, current_suite, show_attributes))
            except Exception as e:
                logger.error(f"Error processing test item: {e}")

    logger.info(f"Found {len(table_data)} test cases:\n")
    print(tabulate(table_data, headers=headers, tablefmt="simple"))


# =============================================================================
# Main List Functions
# =============================================================================

def list_launch_names(launches: List[Dict],
                     attribute_filters: Optional[List[str]] = None,
                     attribute_regex_filters: Optional[List[str]] = None,
                     show_attributes: bool = False) -> None:
    """
    List launch names with statistics in a compact table format.

    Args:
        launches: List of launch dictionaries
        attribute_filters: Optional list of attribute filters in format "key:value" or "value"
        attribute_regex_filters: Optional list of attribute regex filters
        show_attributes: Whether to display attributes column
    """
    # Apply filters
    launches = apply_all_filters(launches, None, attribute_filters, attribute_regex_filters)
    if launches is None:
        return

    if not launches:
        logger.info("No launches found")
        return

    _output_launches_table(launches, show_attributes)


def list_test_items(items: List[Dict],
                   name_regex: Optional[str] = None,
                   attribute_filters: Optional[List[str]] = None,
                   attribute_regex_filters: Optional[List[str]] = None,
                   show_attributes: bool = False,
                   names_only: bool = False) -> None:
    """
    List test items in a compact table format or as names only.

    Args:
        items: List of test item dictionaries
        name_regex: Optional regex pattern to filter items by name
        attribute_filters: Optional list of attribute filters
        attribute_regex_filters: Optional list of attribute regex filters
        show_attributes: Whether to display attributes column
        names_only: If True, output only STEP item names (one per line)
    """
    # Apply filters
    items = apply_all_filters(items, name_regex, attribute_filters, attribute_regex_filters)
    if items is None:
        return

    if not items:
        if not names_only:
            logger.info("No test items found")
        return

    # Output based on mode
    if names_only:
        _output_names_only(items)
    else:
        _output_test_items_table(items, show_attributes)


# =============================================================================
# Options Extraction
# =============================================================================

def _extract_filter_options(options: Namespace) -> Dict[str, Any]:
    """
    Extract filter-related options from parsed arguments.

    Returns:
        Dictionary with filter options
    """
    return {
        'name_regex': getattr(options, 'name_regex', None),
        'attribute_filters': getattr(options, 'attribute', None) if hasattr(options, 'attribute') and options.attribute else None,
        'attribute_regex_filters': getattr(options, 'attribute_regex', None) if hasattr(options, 'attribute_regex') and options.attribute_regex else None,
        'show_attributes': getattr(options, 'show_attributes', False),
        'names_only': getattr(options, 'names_only', False),
        'limit': getattr(options, 'limit', None),
    }


def _build_filter_description(options: Namespace) -> List[str]:
    """Build a list of active filter descriptions for logging."""
    filters = []

    if hasattr(options, 'status') and options.status:
        filters.append(f"status={options.status}")
    if hasattr(options, 'name') and options.name:
        filters.append(f"name~'{options.name}'")
    if hasattr(options, 'name_regex') and options.name_regex:
        filters.append(f"name_regex=/{options.name_regex}/")
    if hasattr(options, 'attribute') and options.attribute:
        for attr in options.attribute:
            filters.append(f"attribute={attr}")
    if hasattr(options, 'attribute_regex') and options.attribute_regex:
        for attr_regex in options.attribute_regex:
            filters.append(f"attribute_regex=/{attr_regex}/")
    if hasattr(options, 'test_target') and options.test_target:
        filters.append(f"test_target={options.test_target}")

    return filters


def _resolve_test_target(client: 'ReportPortalAPIClient', launch_id: str, target_name: str) -> Optional[str]:
    """
    Resolve a test target name to its parent item ID.

    Args:
        client: ReportPortal API client
        launch_id: Launch ID to search within
        target_name: Test target name to find

    Returns:
        Parent item ID as string if found, None otherwise
    """
    # TODO: rewrite to use fetch_test_items once it supports additional filters (see https://github.com/Kuadrant/testsuite-rptool/issues/2)
    parent_items = client.get_test_items(
        launch_id,
        filters={'filter.eq.name': target_name, 'filter.eq.type': 'SUITE'}
    )
    if not parent_items:
        return None
    parent_id = parent_items[0].get('id')
    logger.info(f"Found test target '{target_name}' with ID: {parent_id}")
    return parent_id


# =============================================================================
# Main Entry Point
# =============================================================================

def run_query(options: Namespace) -> int:
    """
    Main function to run the query process.

    Args:
        options: Parsed command line options

    Returns:
        Exit code (0 for success, 1 for failure)
    """

    logger.warning("This is experimental feature, and subject to an active development.")
    logger.info(f"Starting rp_query script with log level: {options.log_level}")
    logger.debug(f"ReportPortal URL: {options.rp_url}")
    logger.debug(f"ReportPortal project: {options.rp_project}")

    # Create API client
    client = ReportPortalAPIClient(
        url=options.rp_url,
        project=options.rp_project,
        token=options.rp_token
    )

    # Resolve launch name to launch ID if specified
    if getattr(options, 'launch_name', None) and not options.launch_id:
        launch = fetch_launch_by_name(client, options.launch_name)
        if launch is None:
            return 1
        options.launch_id = str(launch.get('id'))

    # Extract common filter options
    filter_opts = _extract_filter_options(options)
    filters_desc = _build_filter_description(options)
    filter_msg = f" with filters: {', '.join(filters_desc)}" if filters_desc else ""

    if options.launch_id:
        # Query test items for specific launch
        logger.info(f"Querying test items for launch ID: {options.launch_id}{filter_msg}")

        # Resolve test target to parent ID if specified
        test_target = getattr(options, 'test_target', None)
        parent_id = None
        if test_target:
            parent_id = _resolve_test_target(client, options.launch_id, test_target)
            if parent_id is None:
                logger.error(f"No test target found with name: {test_target}")
                return 1

        # Fetch launch info for header (unless names_only mode)
        if not filter_opts['names_only']:
            try:
                launch = client.get_launch_by_id(options.launch_id)
                _output_launch_header(launch, filter_opts['show_attributes'])
            except Exception as e:
                logger.warning(f"Could not fetch launch header info: {e}")

        items = fetch_test_items(options.launch_id, client, options, limit=filter_opts['limit'])
        if items is None:
            logger.error("Failed to retrieve test items")
            return 1
        # Filter by parent if test target was specified
        # TODO: replace local filtering with ReportPortal API filter parameter once fetch_test_items supports it (see https://github.com/Kuadrant/testsuite-rptool/issues/2)
        if parent_id:
            items = [item for item in items if item.get('parent') == parent_id]

        list_test_items(
            items,
            name_regex=filter_opts['name_regex'],
            attribute_filters=filter_opts['attribute_filters'],
            attribute_regex_filters=filter_opts['attribute_regex_filters'],
            show_attributes=filter_opts['show_attributes'],
            names_only=filter_opts['names_only']
        )
    else:
        # Query launches
        if filter_msg:
            logger.info(f"Querying launches{filter_msg}")

        # Pass limit directly - fetch_launches will use its default if None
        launches = fetch_launches(client, limit=filter_opts['limit'])
        if launches is None:
            logger.error("Failed to retrieve launches")
            return 1

        list_launch_names(
            launches,
            attribute_filters=filter_opts['attribute_filters'],
            attribute_regex_filters=filter_opts['attribute_regex_filters'],
            show_attributes=filter_opts['show_attributes']
        )

    return 0
