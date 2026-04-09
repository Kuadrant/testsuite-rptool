"""
ReportPortal JUnit XML Writer - Core Implementation

This module contains the core RPWriter class that orchestrates the parsing
of JUnit XML files and uploading the results to ReportPortal.
"""

from loguru import logger
from typing import Optional

from .junit_parser import JUnitParser, get_launch_name_from_file, timestamp_rp_to_junit
from .reportportal_client_wrapper import create_rp_client, AutoAnalysisTrigger
from .property_processor import PropertyFilter, LaunchPropertyBuilder


# Configuration constants
TEST_CASE_NAME_CONVERSION = True


class RPWriter:
    """
    Main class for writing JUnit results to ReportPortal.
    
    This class orchestrates the parsing of JUnit XML files and
    uploading the results to ReportPortal with proper property handling.
    """
    
    def __init__(self, options):
        """
        Initialize the RPWriter.
        
        Args:
            options: Parsed command line options
            logger: Logger instance
        """
        self.options = options
        self.property_filter = PropertyFilter()
        self.property_builder = LaunchPropertyBuilder()
        
        # Initialize ReportPortal client
        dry_run = getattr(options, 'dry_run', False)
        self.rp_client = create_rp_client(
            options.rp_url,
            options.rp_project,
            options.rp_token,
            dry_run=dry_run
        )

        # Initialize auto-analysis trigger if enabled
        if options.trigger_auto_analysis:
            self.auto_analysis = AutoAnalysisTrigger(
                options.rp_url,
                options.rp_project,
                options.rp_token,
                dry_run=dry_run
            )
        else:
            self.auto_analysis = None
    
    def process_junit_file(self) -> int:
        """
        Process the JUnit XML file and upload results to ReportPortal.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        launch_started = False
        try:
            # Parse JUnit XML file
            parser = JUnitParser(
                self.options.junits,
                enable_name_conversion=TEST_CASE_NAME_CONVERSION
            )

            # Generate launch name
            launch_name = get_launch_name_from_file(
                self.options.junits[0], # automatic name from the first one
                self.options.launch_name
            )

            dry_run = getattr(self.options, 'dry_run', False)
            if dry_run:
                logger.info("="*60)
                logger.info("DRY-RUN MODE ENABLED - No data will be sent to ReportPortal")
                logger.info("="*60)

            logger.info(f"Processing JUnit files: {self.options.junits}")
            logger.info(f"Launch name: {launch_name}")

            # Start ReportPortal session
            self.rp_client.start_session()
            launch_started = True

            # Process all test suites
            launch_info = self._process_test_suites(parser, launch_name)

            # Trigger auto-analysis if enabled
            if self.auto_analysis and launch_info:
                launch_id = launch_info.get('id')
                if launch_id:
                    self.auto_analysis.trigger_auto_analysis(launch_id)

            logger.info("JUnit processing completed successfully")
            return 0

        except Exception as e:
            logger.error(f"Failed to process JUnit file: {e}")
            logger.exception(e)
            return 1
        finally:
            if launch_started:
                logger.debug("Closing ReportPortal session...")
                self.rp_client.terminate_session()
            else:
                logger.debug("Session was not started, skipping termination")
    
    def _process_test_suites(self, parser: JUnitParser, launch_name: str) -> Optional[dict]:
        """
        Process all test suites and upload to ReportPortal.

        Args:
            parser: Initialized JUnit parser
            launch_name: Name for the ReportPortal launch

        Returns:
            Launch info dictionary or None if failed
        """
        launch_properties = None
        # Has to be not None to utilize concatenation of launch descriptions
        initial_launch_description = self.options.launch_description or ""

        # Pre-collect all suites to find earliest timestamp and calculate total runtime
        all_suites = list(parser.parse_suites())

        if not all_suites:
            logger.warning("No test suites found in JUnit file(s)")
            return None

        # Find earliest timestamp and latest end time across all suites
        launch_timestamp = min(suite['timestamp'] for suite in all_suites)
        logger.debug(f'Earliest launch_timestamp {timestamp_rp_to_junit(launch_timestamp)}')
        max_end_time = max(suite['timestamp'] + suite['time'] for suite in all_suites)
        logger.debug(f'Latest finish time {timestamp_rp_to_junit(max_end_time)}')

        # Pre-process suites to extract launch properties and descriptions
        final_launch_description = initial_launch_description
        for suite_data in all_suites:
            # Filter suite properties
            filtered_props, _, launch_desc = self.property_filter.filter_suite_properties(
                suite_data['properties']
            )

            # Handle info-collector suite special case
            promoted_props, promoted_desc = self.property_filter.promote_info_collector_properties(
                suite_data['name'], filtered_props, launch_desc
            )

            if promoted_props is not None:
                launch_properties = promoted_props
                if promoted_desc:
                    final_launch_description = promoted_desc

        # Start launch with earliest timestamp
        launch_id = self.rp_client.start_launch(
            name=launch_name,
            start_time=str(launch_timestamp),
            # Initial launch description will be followed (concatenated)
            # with final_launch_description in .finish_launch()
            description=initial_launch_description
        )

        # Process all suites
        for suite_data in all_suites:
            logger.debug(f"Processing suite: {suite_data['name']}")

            # Filter suite properties
            filtered_props, suite_desc, _ = self.property_filter.filter_suite_properties(
                suite_data['properties']
            )

            # Process the suite
            self._process_test_suite(
                suite_data, filtered_props, suite_desc 
            )
        
        # Finish launch with proper end time
        final_properties = self.property_builder.build_final_launch_properties(
            launch_properties,
            trigger_auto_analysis=self.options.trigger_auto_analysis
        )
        return self.rp_client.finish_launch(
            end_time=str(max_end_time),
            attributes=final_properties,
            description=final_launch_description
        )
    
    def _process_test_suite(self, suite_data: dict, suite_properties: list,
                           suite_description: Optional[str]) -> None:
        """
        Process a single test suite.

        Args:
            suite_data: Suite data dictionary
            suite_properties: Filtered suite properties
            suite_description: Suite description
            launch_timestamp: Launch start timestamp (unused but kept for compatibility)
        """
        suite_timestamp = suite_data['timestamp']
        logger.debug(f'Suite timestamp {suite_timestamp}')
        suite_runtime = 0

        # Start test suite
        suite_id = self.rp_client.start_test_suite(
            name=suite_data['name'],
            start_time=str(suite_timestamp),
            attributes=suite_properties,
            description=suite_description
        )

        # Process all test cases in the suite
        for case_data in suite_data['test_cases']:
            case_runtime = self._process_test_case(
                case_data, suite_id, suite_timestamp + suite_runtime
            )
            # Disabling suite_runtime tally, due to Interrupted test cases
            # because of parallel run, total runtime is larger than actual time
            # suite_runtime += case_runtime

        # Finish test suite
        self.rp_client.finish_test_suite(
            suite_id,
            end_time=str(suite_timestamp + suite_runtime),
            attributes=suite_properties
        )
    
    def _create_failed_attempts(self, test_name: str, case_result,
                               suite_id: str, start_time: int, rerun_duration: int) -> str:
        """
        Create all failed rerun attempts before the final test result.

        The first attempt is the original item (retry=False). Subsequent attempts
        are retries referencing the original via retry_of (RP 25.x).

        Args:
            test_name: Full test case name
            case_result: Filtered case property result
            suite_id: Parent suite ID
            start_time: Test case start time
            rerun_duration: Duration allocated per retry attempt

        Returns:
            UUID of the original (first) test item
        """
        original_id = None
        for attempt in range(case_result.reruns):
            is_original = (attempt == 0)
            attempt_start = start_time + (attempt * rerun_duration)
            item_id = self.rp_client.start_test_case(
                name=test_name,
                start_time=str(attempt_start),
                parent_id=suite_id,
                attributes=case_result.properties,
                description=case_result.description,
                code_ref=test_name,
                retry=not is_original,
                retry_of=None if is_original else original_id
            )
            if is_original:
                original_id = item_id
            if attempt < len(case_result.rerun_messages):
                self.rp_client.log_message(item_id, case_result.rerun_messages[attempt], "ERROR")
            if attempt < len(case_result.rerun_outputs):
                self.rp_client.log_message(item_id, case_result.rerun_outputs[attempt], "INFO")
            self.rp_client.finish_test_case(
                item_id,
                end_time=str(attempt_start + rerun_duration),
                status="FAILED",
                attributes=case_result.properties
            )
            logger.debug(f"Created {'original' if is_original else 'retry'} attempt "
                         f"{attempt + 1}/{case_result.reruns} for '{test_name}'")
        return original_id

    def _process_test_case(self, case_data: dict, suite_id: str, start_time: int) -> int:
        """
        Process a single test case.

        Args:
            case_data: Test case data dictionary
            suite_id: Parent suite ID
            start_time: Test case start time

        Returns:
            Test case runtime in milliseconds
        """
        # Filter case properties
        case_result = self.property_filter.filter_case_properties(
            case_data['properties']
        )

        # Generate test case name (pytest-style)
        test_name = f"{case_data['converted_classname']}::{case_data['name']}"

        # Create failed rerun attempts before the final result
        original_id = None
        final_start_time = start_time
        if case_result.reruns > 0:
            rerun_duration = case_data['time'] // (case_result.reruns + 1)
            original_id = self._create_failed_attempts(
                test_name, case_result, suite_id, start_time, rerun_duration
            )
            final_start_time = start_time + (case_result.reruns * rerun_duration)

        # Start the final test case (or the only one if no retries)
        case_id = self.rp_client.start_test_case(
            name=test_name,
            start_time=str(final_start_time),
            parent_id=suite_id,
            attributes=case_result.properties,
            description=case_result.description,
            code_ref=test_name,
            retry=original_id is not None,
            retry_of=original_id
        )

        # Log test outputs and results for the final attempt
        self.rp_client.log_test_outputs(
            case_id,
            case_data['system_out'],
            case_data['system_err'],
            case_data['failures'],
            case_data['errors'],
            case_data['skipped']
        )

        # Finish test case
        end_time = start_time + case_data['time']
        self.rp_client.finish_test_case(
            case_id,
            end_time=str(end_time),
            status=case_data['status'],
            attributes=case_result.properties
        )

        return case_data['time']