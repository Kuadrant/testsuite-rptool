"""
Integration tests for the complete ReportPortal workflow.

These tests verify the integration between all components:
- JUnit XML parsing
- Property processing and filtering
- ReportPortal client operations
- End-to-end test result reporting
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from reportportal.junit_parser import JUnitParser
from reportportal.property_processor import PropertyFilter, LaunchPropertyBuilder
from reportportal.reportportal_client_wrapper import ReportPortalClientWrapper, AutoAnalysisTrigger


@pytest.mark.integration
class TestFullReportPortalWorkflow:
    """Integration tests for the complete ReportPortal workflow."""
    
    @pytest.mark.smoke
    @patch('reportportal.reportportal_client_wrapper.RPClient')
    def test_complete_workflow_integration(self, mock_rp_client, sample_junit_xml_file):
        """Test the complete workflow from JUnit XML to ReportPortal."""
        # Setup mock ReportPortal client
        mock_client = Mock()
        mock_client.start_launch.return_value = "launch_123"
        mock_client.start_test_item.side_effect = ["suite_456", "case_789", "case_101", "case_202"]
        mock_client.get_launch_info.return_value = {"id": "launch_123", "status": "FAILED"}
        mock_rp_client.return_value = mock_client
        
        # Initialize components
        junit_parser = JUnitParser([sample_junit_xml_file], enable_name_conversion=True)
        property_filter = PropertyFilter()
        launch_builder = LaunchPropertyBuilder()
        rp_wrapper = ReportPortalClientWrapper("https://example.com", "project", "api_key")
        
        # Start ReportPortal session
        rp_wrapper.start_session()
        
        # Parse JUnit XML and process suites
        suites = list(junit_parser.parse_suites())
        assert len(suites) == 1
        
        suite_data = suites[0]
        
        # Process suite properties
        filtered_props, suite_desc, launch_desc = property_filter.filter_suite_properties(
            suite_data['properties']
        )
        
        # Verify property filtering worked correctly
        assert len(filtered_props) == 2  # platform, version
        assert suite_desc == "Integration test suite"
        assert launch_desc == "Full workflow test"
        
        # Build final launch properties with auto-analysis enabled
        final_launch_props = launch_builder.build_final_launch_properties(filtered_props, trigger_auto_analysis=True)
        assert len(final_launch_props) == 4  # 2 original + 2 auto-analysis
        
        # Start launch in ReportPortal
        launch_id = rp_wrapper.start_launch(
            name="Integration Test Launch",
            start_time=suite_data['timestamp'],
            description=launch_desc
        )
        assert launch_id == "launch_123"
        
        # Start test suite
        suite_id = rp_wrapper.start_test_suite(
            name=suite_data['name'],
            start_time=suite_data['timestamp'],
            attributes=filtered_props,
            description=suite_desc
        )
        assert suite_id == "suite_456"
        
        # Process each test case
        test_cases = suite_data['test_cases']
        assert len(test_cases) == 3
        
        case_ids = []
        for case in test_cases:
            # Filter case properties
            case_result = property_filter.filter_case_properties(case['properties'])

            # Start test case
            case_id = rp_wrapper.start_test_case(
                name=case['name'],
                start_time=suite_data['timestamp'],  # Using suite timestamp for simplicity
                parent_id=suite_id,
                attributes=case_result.properties,
                description=case_result.description
            )
            case_ids.append(case_id)
            
            # Log test outputs
            rp_wrapper.log_test_outputs(
                case_id=case_id,
                system_out=case.get('system_out'),
                system_err=case.get('system_err'),
                failures=case.get('failures', []),
                errors=case.get('errors', []),
                skipped=case.get('skipped', [])
            )
            
            # Finish test case
            rp_wrapper.finish_test_case(
                case_id=case_id,
                end_time=suite_data['timestamp'],  # Using suite timestamp for simplicity
                status=case['status'],
                attributes=case_result.properties
            )
        
        # Finish test suite
        rp_wrapper.finish_test_suite(
            suite_id=suite_id,
            end_time=suite_data['timestamp'],
            attributes=filtered_props
        )
        
        # Finish launch
        launch_info = rp_wrapper.finish_launch(
            end_time=suite_data['timestamp'],
            attributes=final_launch_props,
            description=launch_desc
        )
        
        # Terminate session
        rp_wrapper.terminate_session()
        
        # Verify all ReportPortal operations were called correctly
        mock_client.start.assert_called_once()
        mock_client.start_launch.assert_called_once()
        assert mock_client.start_test_item.call_count == 4  # 1 suite + 3 cases
        assert mock_client.finish_test_item.call_count == 4  # 1 suite + 3 cases
        mock_client.finish_launch.assert_called_once()
        mock_client.get_launch_info.assert_called_once()
        mock_client.terminate.assert_called_once()
        
        # Verify launch info
        assert launch_info["id"] == "launch_123"
        assert launch_info["status"] == "FAILED"
    
    def test_property_processing_integration(self, sample_junit_xml_file):
        """Test property processing integration across all components."""
        # Parse JUnit XML
        parser = JUnitParser([sample_junit_xml_file])
        suites = list(parser.parse_suites())
        suite_data = suites[0]
        
        # Initialize property processor
        property_filter = PropertyFilter()
        
        # Test suite property processing
        filtered_props, suite_desc, launch_desc = property_filter.filter_suite_properties(
            suite_data['properties']
        )
        
        # Verify filtering worked correctly
        expected_props = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"}
        ]
        
        assert len(filtered_props) == 2
        for prop in expected_props:
            assert prop in filtered_props
        
        assert suite_desc == "Integration test suite"
        assert launch_desc == "Full workflow test"
        
        # Test case property processing for each case
        test_cases = suite_data['test_cases']
        
        # Test passing case
        passing_case = next(case for case in test_cases if case['name'] == 'test_passing')
        case_result = property_filter.filter_case_properties(passing_case['properties'])
        expected_case_props = [
            {"key": "color", "value": "green"},
            {"key": "component", "value": "TestComponent"}
        ]
        assert len(case_result.properties) == 2
        for prop in expected_case_props:
            assert prop in case_result.properties
        assert case_result.description is None

        # Test failing case with description
        failing_case = next(case for case in test_cases if case['name'] == 'test_failing')
        case_result = property_filter.filter_case_properties(failing_case['properties'])
        assert len(case_result.properties) == 1
        assert {"key": "color", "value": "red"} in case_result.properties
        assert case_result.description == "Test case that fails"

        # Test skipped case
        skipped_case = next(case for case in test_cases if case['name'] == 'test_skipped')
        case_result = property_filter.filter_case_properties(skipped_case['properties'])
        assert len(case_result.properties) == 1
        assert {"key": "color", "value": "yellow"} in case_result.properties
        assert case_result.description is None
    
    @patch('reportportal.reportportal_client_wrapper.requests.post')
    def test_auto_analysis_integration(self, mock_post):
        """Test auto-analysis trigger integration."""
        # Setup successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Initialize auto-analysis trigger
        trigger = AutoAnalysisTrigger("https://example.com", "test_project", "api_key")
        
        # Test auto-analysis trigger
        result = trigger.trigger_auto_analysis("launch_123")
        
        assert result is True
        mock_post.assert_called_once_with(
            url="https://example.com/api/v1/test_project/launch/analyze",
            headers={
                'Authorization': 'bearer api_key',
                'Content-type': 'application/json',
                'accept': '*/*'
            },
            json={
                "analyzeItemsMode": ["TO_INVESTIGATE"],
                "analyzerMode": "ALL",
                "analyzerTypeName": "autoAnalyzer",
                "launchId": "launch_123",
            }
        )
    
    def test_info_collector_workflow(self, sample_junit_xml_file):
        """Test workflow with info-collector suite promotion."""
        # Parse JUnit XML
        parser = JUnitParser([sample_junit_xml_file])
        suites = list(parser.parse_suites())
        suite_data = suites[0]
        
        # Process properties
        property_filter = PropertyFilter()
        filtered_props, suite_desc, launch_desc = property_filter.filter_suite_properties(
            suite_data['properties']
        )
        
        # Test info-collector promotion
        promoted_props, promoted_desc = property_filter.promote_info_collector_properties(
            "info-collector", filtered_props, launch_desc
        )
        
        # Should promote properties for info-collector
        assert promoted_props == filtered_props
        assert promoted_desc == launch_desc
        
        # Build final launch properties with promoted properties
        launch_builder = LaunchPropertyBuilder()
        final_properties = launch_builder.build_final_launch_properties(promoted_props, trigger_auto_analysis=True)
        
        # Should include original properties + auto-analysis properties
        assert len(final_properties) == 4  # 2 original + 2 auto-analysis
        
        # Verify auto-analysis properties are included
        auto_analysis_props = [
            {"key": "auto_analyze", "system": "true", "value": "true"},
            {"key": "immediateAutoAnalysis", "system": "true", "value": "true"}
        ]
        
        for prop in auto_analysis_props:
            assert prop in final_properties
    
    def test_error_handling_integration(self):
        """Test error handling integration across components."""
        # Test JUnit parser with invalid file
        with pytest.raises(Exception):
            parser = JUnitParser(["/nonexistent/file.xml"])
            list(parser.parse_suites())
        
        # Test ReportPortal wrapper operations without client session
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.start_launch("Test Launch", "2024-01-01T12:00:00")
        
        # Test property filter with invalid input
        property_filter = PropertyFilter()
        
        # Should handle None/empty inputs gracefully
        filtered_props, suite_desc, launch_desc = property_filter.filter_suite_properties(None)
        assert filtered_props == []
        assert suite_desc is None
        assert launch_desc is None
        
        case_result = property_filter.filter_case_properties([])
        assert case_result.properties == []
        assert case_result.description is None


@pytest.mark.integration
class TestComponentInteraction:
    """Test interactions between different components."""
    
    def test_parser_to_property_filter_data_flow(self, sample_junit_xml_file):
        """Test data flow from parser to property filter."""
        # Parse data with JUnit parser
        parser = JUnitParser([sample_junit_xml_file], enable_name_conversion=True)
        suites = list(parser.parse_suites())
        suite_data = suites[0]
        
        # Verify parser output format is compatible with property filter
        property_filter = PropertyFilter()
        
        # Test suite properties
        assert 'properties' in suite_data
        assert isinstance(suite_data['properties'], list)
        
        filtered_props, _, _ = property_filter.filter_suite_properties(suite_data['properties'])
        assert isinstance(filtered_props, list)
        
        # Test case properties
        for case in suite_data['test_cases']:
            assert 'properties' in case
            assert isinstance(case['properties'], list)
            
            case_result = property_filter.filter_case_properties(case['properties'])
            assert isinstance(case_result.properties, list)
    
    def test_property_filter_to_client_wrapper_data_flow(self):
        """Test data flow from property filter to client wrapper."""
        property_filter = PropertyFilter()
        launch_builder = LaunchPropertyBuilder()
        
        # Create sample properties
        suite_properties = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"},
            {"key": "__rp_suite_description", "value": "Test suite"},
            {"key": "__rp_launch_description", "value": "Test launch"}
        ]
        
        # Process properties
        filtered_props, suite_desc, launch_desc = property_filter.filter_suite_properties(
            suite_properties
        )
        final_props = launch_builder.build_final_launch_properties(filtered_props, trigger_auto_analysis=False)
        
        # Test compatibility with client wrapper
        with patch('reportportal.reportportal_client_wrapper.RPClient') as mock_rp_client:
            mock_client = Mock()
            mock_client.start_launch.return_value = "test_launch_id"
            mock_client.start_test_item.return_value = "test_suite_id"
            mock_rp_client.return_value = mock_client
            
            wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
            wrapper.start_session()
            
            # These should accept the processed data without errors
            launch_id = wrapper.start_launch("Test", "2024-01-01T12:00:00", launch_desc)
            suite_id = wrapper.start_test_suite("Suite", "2024-01-01T12:00:00", 
                                              filtered_props, suite_desc)
            
            # Verify data types are correct
            assert isinstance(launch_id, str)
            assert isinstance(suite_id, str)
    
    def test_name_conversion_integration(self, sample_junit_xml_file):
        """Test name conversion integration across workflow."""
        # Test with name conversion enabled
        parser = JUnitParser([sample_junit_xml_file], enable_name_conversion=True)
        suites = list(parser.parse_suites())
        
        for suite in suites:
            for case in suite['test_cases']:
                # Should have converted classname
                assert 'converted_classname' in case
                assert case['converted_classname'].endswith('.py')
                assert '/' in case['converted_classname']  # Dots should be converted to slashes
        
        # Test with name conversion disabled
        parser = JUnitParser([sample_junit_xml_file], enable_name_conversion=False)
        suites = list(parser.parse_suites())
        
        for suite in suites:
            for case in suite['test_cases']:
                # Should preserve original classname format
                assert 'converted_classname' in case
                assert case['converted_classname'] == case['classname']
                assert '.' in case['converted_classname']  # Original dots preserved
    
    def test_trigger_auto_analysis_integration(self, sample_junit_xml_file):
        """Test trigger auto-analysis functionality integration."""
        property_filter = PropertyFilter()
        launch_builder = LaunchPropertyBuilder()
        
        # Sample properties
        suite_properties = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"}
        ]
        
        # Test without auto-analysis
        final_props_no_auto = launch_builder.build_final_launch_properties(
            suite_properties, trigger_auto_analysis=False
        )
        
        # Should only have base properties
        assert len(final_props_no_auto) == 2
        assert {"key": "platform", "value": "aws"} in final_props_no_auto
        assert {"key": "version", "value": "1.3.0"} in final_props_no_auto
        
        # Should NOT have auto-analysis properties
        auto_props = [
            {"key": "auto_analyze", "system": "true", "value": "true"},
            {"key": "immediateAutoAnalysis", "system": "true", "value": "true"}
        ]
        for prop in auto_props:
            assert prop not in final_props_no_auto
        
        # Test with auto-analysis enabled
        final_props_with_auto = launch_builder.build_final_launch_properties(
            suite_properties, trigger_auto_analysis=True
        )
        
        # Should have base properties + auto-analysis properties
        assert len(final_props_with_auto) == 4
        assert {"key": "platform", "value": "aws"} in final_props_with_auto
        assert {"key": "version", "value": "1.3.0"} in final_props_with_auto
        
        # Should have auto-analysis properties
        for prop in auto_props:
            assert prop in final_props_with_auto