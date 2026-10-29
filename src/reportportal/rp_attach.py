"""
Attach collected cluster YAML files to failed ReportPortal test items.
"""

from argparse import Namespace
from pathlib import Path
from typing import Iterable, List, Optional

from loguru import logger

from .rp_api_client import ReportPortalAPIClient, ReportPortalAPIError
from .rp_query import fetch_launch_by_name
from . import rp_query_utils as utils


def filename_needle_from_rp_name(rp_name: str) -> str:
    """Map an RP item name to the collector filename fragment.

    Last three path components of the module plus the test name, with ``[]`` → ``()``.
    Same files in different directories must not share a needle. Must stay in sync
    with testsuite ``_nodeid_filename_fragment``.
    """
    path_part, sep, test_part = rp_name.partition("::")
    if not sep:
        test_part = path_part.rsplit("/", 1)[-1]
    if path_part.endswith(".py"):
        path_part = path_part[:-3]
    unique_module = "_".join(path_part.split("/")[-3:])
    name = f"{unique_module}_{test_part}"
    return name.replace("[", "(").replace("]", ")").replace("/", "_").replace("\\", "_")


def match_yaml_files(rp_name: str, yaml_files: Iterable[Path]) -> List[Path]:
    """Return YAML files whose names contain the needle derived from ``rp_name``."""
    needle = filename_needle_from_rp_name(rp_name)
    if not needle:
        return []
    return [path for path in yaml_files if needle in path.name]


def _item_uuid(item: dict) -> Optional[str]:
    """Prefer RP uuid; fall back to id."""
    value = item.get("uuid") or item.get("id")
    return str(value) if value is not None else None


def _launch_uuid(launch: dict) -> Optional[str]:
    """Prefer RP uuid; fall back to id."""
    value = launch.get("uuid") or launch.get("id")
    return str(value) if value is not None else None


def _list_yaml_files(yaml_dir: Path) -> List[Path]:
    return sorted(path for path in yaml_dir.iterdir() if path.suffix in {".yaml", ".yml"} and path.is_file())


def run_attach(args: Namespace) -> int:
    """Attach YAML from ``args.dir`` to FAILED items. Returns 0 on success/no-op, 1 on error."""
    yaml_dir = Path(args.dir)
    if not yaml_dir.exists():
        logger.warning("Directory not found: {} — nothing to attach", yaml_dir)
        return 0
    if not yaml_dir.is_dir():
        logger.error("{} is not a directory", yaml_dir)
        return 1

    yaml_files = _list_yaml_files(yaml_dir)
    if not yaml_files:
        logger.info("No YAML files in {} — nothing to attach", yaml_dir)
        return 0

    client = ReportPortalAPIClient(args.rp_url, args.rp_project, args.rp_token)

    launch_id = getattr(args, "launch_id", None)
    if launch_id:
        try:
            launch = client.get_launch_by_id(launch_id)
        except ReportPortalAPIError as exc:
            logger.error("Failed to fetch launch {}: {}", launch_id, exc)
            return 1
    else:
        launch = fetch_launch_by_name(client, args.launch_name)
        if not launch:
            logger.error("Launch not found: {}", args.launch_name)
            return 1

    resolved_launch_id = str(launch.get("id"))
    launch_uuid = _launch_uuid(launch)
    logger.info("Attaching resources to launch {} ({})", launch.get("name"), resolved_launch_id)

    try:
        items = client.get_test_items(
            resolved_launch_id,
            filters={"filter.eq.status": "FAILED"},
        )
    except ReportPortalAPIError as exc:
        logger.error("Failed to list test items: {}", exc)
        return 1

    failed_items = utils.exclude_type(items, utils.ITEM_TYPE_SUITE)
    if not failed_items:
        logger.info("No failed test items in launch — nothing to attach")
        return 0

    attached = 0
    upload_errors = 0
    for item in failed_items:
        rp_name = item.get("name") or ""
        item_uuid = _item_uuid(item)
        if not item_uuid:
            logger.warning("Skipping item without id/uuid: {}", rp_name)
            continue

        matched = match_yaml_files(rp_name, yaml_files)
        if not matched:
            logger.debug("No YAML files matched '{}'", rp_name)
            continue

        for yaml_file in matched:
            logger.info("Attaching {} to {}", yaml_file.name, rp_name)
            try:
                client.attach_file_to_item(item_uuid, yaml_file, launch_uuid=launch_uuid)
                attached += 1
            except ReportPortalAPIError as exc:
                logger.error("Failed to attach {}: {}", yaml_file.name, exc)
                upload_errors += 1

    logger.info("Attached {} file(s) to failed test items", attached)
    return 1 if upload_errors else 0
