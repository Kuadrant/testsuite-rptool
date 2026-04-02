"""
Unit tests for property_processor module.
"""

import pytest
from unittest.mock import Mock, patch

from reportportal.property_processor import (
    PropertyFilter,
    LaunchPropertyBuilder,
    create_property_processor
)


@pytest.mark.unit
class TestPropertyFilter:
    """Test PropertyFilter class."""
    
    def test_filter_suite_properties_basic(self):
        """Test basic suite property filtering."""
        filter_obj = PropertyFilter()
        
        properties = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"},
            {"key": "__rp_suite_description", "value": "Suite description"},
            {"key": "__rp_launch_description", "value": "Launch description"},
            {"key": "__rp_prefix_filtered", "value": "should be filtered"}
        ]
        
        filtered_props, suite_desc, launch_desc = filter_obj.filter_suite_properties(properties)
        
        # Should keep non-RP properties
        assert len(filtered_props) == 2
        assert {"key": "platform", "value": "aws"} in filtered_props
        assert {"key": "version", "value": "1.3.0"} in filtered_props
        
        # Should extract descriptions
        assert suite_desc == "Suite description"
        assert launch_desc == "Launch description"
    
    def test_filter_suite_properties_no_descriptions(self):
        """Test suite property filtering with no descriptions."""
        filter_obj = PropertyFilter()
        
        properties = [
            {"key": "platform", "value": "aws"},
            {"key": "color", "value": "green"}
        ]
        
        filtered_props, suite_desc, launch_desc = filter_obj.filter_suite_properties(properties)
        
        assert len(filtered_props) == 2
        assert suite_desc is None
        assert launch_desc is None
    
    def test_filter_suite_properties_empty(self):
        """Test suite property filtering with empty list."""
        filter_obj = PropertyFilter()
        
        filtered_props, suite_desc, launch_desc = filter_obj.filter_suite_properties([])
        
        assert filtered_props == []
        assert suite_desc is None
        assert launch_desc is None
    
    def test_filter_case_properties_basic(self):
        """Test basic case property filtering."""
        filter_obj = PropertyFilter()
        
        properties = [
            {"key": "color", "value": "green"},
            {"key": "component", "value": "TestComponent"},
            {"key": "__rp_case_description", "value": "Case description"},
            {"key": "__rp_filtered", "value": "should be filtered"}
        ]
        
        case_result = filter_obj.filter_case_properties(properties)

        # Should keep non-RP properties
        assert len(case_result.properties) == 2
        assert {"key": "color", "value": "green"} in case_result.properties
        assert {"key": "component", "value": "TestComponent"} in case_result.properties

        # Should extract description
        assert case_result.description == "Case description"
    
    def test_filter_case_properties_no_description(self):
        """Test case property filtering with no description."""
        filter_obj = PropertyFilter()
        
        properties = [
            {"key": "color", "value": "red"},
            {"key": "priority", "value": "high"}
        ]
        
        case_result = filter_obj.filter_case_properties(properties)

        assert len(case_result.properties) == 2
        assert case_result.description is None
    
    def test_filter_case_properties_empty(self):
        """Test case property filtering with empty list."""
        filter_obj = PropertyFilter()
        
        case_result = filter_obj.filter_case_properties([])

        assert case_result.properties == []
        assert case_result.description is None
    
    def test_filter_case_properties_with_reruns_and_messages(self):
        """Test case property filtering with rerun metadata."""
        filter_obj = PropertyFilter()

        properties = [
            {"key": "__rp_reruns", "value": "2"},
            {"key": "__rp_rerun_1_message", "value": "first failure"},
            {"key": "__rp_rerun_2_message", "value": "second failure"},
            {"key": "component", "value": "TestComponent"},
        ]

        case_result = filter_obj.filter_case_properties(properties)

        assert case_result.reruns == 2
        assert case_result.rerun_messages == ["first failure", "second failure"]
        assert {"key": "component", "value": "TestComponent"} in case_result.properties

    def test_filter_case_properties_with_invalid_reruns_value(self):
        """Test case property filtering with invalid rerun count."""
        filter_obj = PropertyFilter()

        properties = [{"key": "__rp_reruns", "value": "not-an-int"}]

        case_result = filter_obj.filter_case_properties(properties)

        assert case_result.reruns == 0

    def test_promote_info_collector_properties(self):
        """Test promotion of info-collector properties."""
        filter_obj = PropertyFilter()
        
        suite_properties = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"}
        ]
        launch_description = "Info collector description"
        
        # Test with info-collector suite
        promoted_props, promoted_desc = filter_obj.promote_info_collector_properties(
            "info-collector", suite_properties, launch_description
        )
        
        assert promoted_props == suite_properties
        assert promoted_desc == launch_description
    
    def test_promote_non_info_collector_properties(self):
        """Test no promotion for non-info-collector suites."""
        filter_obj = PropertyFilter()
        
        suite_properties = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"}
        ]
        launch_description = "Regular suite description"
        
        # Test with regular suite
        promoted_props, promoted_desc = filter_obj.promote_info_collector_properties(
            "regular-suite", suite_properties, launch_description
        )
        
        assert promoted_props is None
        assert promoted_desc is None
    
    def test_promote_info_collector_no_description(self):
        """Test info-collector promotion with no description."""
        filter_obj = PropertyFilter()
        
        suite_properties = [{"key": "platform", "value": "aws"}]
        
        promoted_props, promoted_desc = filter_obj.promote_info_collector_properties(
            "info-collector", suite_properties, None
        )
        
        assert promoted_props == suite_properties
        assert promoted_desc is None


@pytest.mark.unit
class TestLaunchPropertyBuilder:
    """Test LaunchPropertyBuilder class."""
    
    def test_build_final_launch_properties_with_base(self):
        """Test building final launch properties with base properties."""
        builder = LaunchPropertyBuilder()
        
        base_properties = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"}
        ]
        
        # Test with auto-analysis disabled (default)
        final_properties = builder.build_final_launch_properties(base_properties, trigger_auto_analysis=False)
        
        # Should include only base properties
        assert {"key": "platform", "value": "aws"} in final_properties
        assert {"key": "version", "value": "1.3.0"} in final_properties
        
        # Should NOT include auto-analysis properties
        assert {"key": "auto_analyze", "system": "true", "value": "true"} not in final_properties
        assert {"key": "immediateAutoAnalysis", "system": "true", "value": "true"} not in final_properties
        
        # Total should be only base properties
        assert len(final_properties) == 2
    
    def test_build_final_launch_properties_with_auto_analysis(self):
        """Test building final launch properties with auto-analysis enabled."""
        builder = LaunchPropertyBuilder()
        
        base_properties = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"}
        ]
        
        # Test with auto-analysis enabled
        final_properties = builder.build_final_launch_properties(base_properties, trigger_auto_analysis=True)
        
        # Should include base properties
        assert {"key": "platform", "value": "aws"} in final_properties
        assert {"key": "version", "value": "1.3.0"} in final_properties
        
        # Should include auto-analysis properties
        assert {"key": "auto_analyze", "system": "true", "value": "true"} in final_properties
        assert {"key": "immediateAutoAnalysis", "system": "true", "value": "true"} in final_properties
        
        # Total should be base properties + 2 auto-analysis properties
        assert len(final_properties) == 4
    
    def test_build_final_launch_properties_no_base(self):
        """Test building final launch properties without base properties."""
        builder = LaunchPropertyBuilder()
        
        # Test without auto-analysis
        final_properties = builder.build_final_launch_properties(None, trigger_auto_analysis=False)
        assert len(final_properties) == 0
        
        # Test with auto-analysis
        final_properties_with_auto = builder.build_final_launch_properties(None, trigger_auto_analysis=True)
        assert len(final_properties_with_auto) == 2
        assert {"key": "auto_analyze", "system": "true", "value": "true"} in final_properties_with_auto
        assert {"key": "immediateAutoAnalysis", "system": "true", "value": "true"} in final_properties_with_auto
    
    def test_build_final_launch_properties_empty_base(self):
        """Test building final launch properties with empty base properties."""
        builder = LaunchPropertyBuilder()
        
        # Test without auto-analysis
        final_properties = builder.build_final_launch_properties([], trigger_auto_analysis=False)
        assert len(final_properties) == 0
        
        # Test with auto-analysis
        final_properties_with_auto = builder.build_final_launch_properties([], trigger_auto_analysis=True)
        assert len(final_properties_with_auto) == 2
        assert {"key": "auto_analyze", "system": "true", "value": "true"} in final_properties_with_auto
        assert {"key": "immediateAutoAnalysis", "system": "true", "value": "true"} in final_properties_with_auto


@pytest.mark.unit
class TestCreatePropertyProcessor:
    """Test create_property_processor factory function."""
    
    def test_create_property_processor(self):
        """Test property processor factory function."""
        processor = create_property_processor()
        
        assert isinstance(processor, PropertyFilter)
        assert hasattr(processor, 'filter_suite_properties')
        assert hasattr(processor, 'filter_case_properties')
        assert hasattr(processor, 'promote_info_collector_properties')


@pytest.mark.unit
class TestPropertyFilterIntegration:
    """Integration tests for PropertyFilter."""
    
    def test_full_property_filtering_workflow(self):
        """Test complete property filtering workflow."""
        filter_obj = PropertyFilter()
        
        # Simulate properties from an info-collector suite
        suite_properties = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"},
            {"key": "build", "value": "kuadrant"},
            {"key": "__rp_suite_description", "value": "Info collector suite"},
            {"key": "__rp_launch_description", "value": "Launch from info collector"},
            {"key": "__rp_internal", "value": "filtered out"}
        ]
        
        # Filter suite properties
        filtered_props, suite_desc, launch_desc = filter_obj.filter_suite_properties(suite_properties)
        
        # Should keep regular properties
        assert len(filtered_props) == 3
        expected_props = [
            {"key": "platform", "value": "aws"},
            {"key": "version", "value": "1.3.0"},
            {"key": "build", "value": "kuadrant"}
        ]
        for prop in expected_props:
            assert prop in filtered_props
        
        # Should extract descriptions
        assert suite_desc == "Info collector suite"
        assert launch_desc == "Launch from info collector"
        
        # Promote info-collector properties
        promoted_props, promoted_desc = filter_obj.promote_info_collector_properties(
            "info-collector", filtered_props, launch_desc
        )
        
        assert promoted_props == filtered_props
        assert promoted_desc == launch_desc
        
        # Build final launch properties
        builder = LaunchPropertyBuilder()
        final_properties = builder.build_final_launch_properties(promoted_props, trigger_auto_analysis=True)
        
        # Should have original properties + auto-analysis properties
        assert len(final_properties) == 5  # 3 original + 2 auto-analysis
        
        # Verify all expected properties are present
        for prop in expected_props:
            assert prop in final_properties
        
        assert {"key": "auto_analyze", "system": "true", "value": "true"} in final_properties
        assert {"key": "immediateAutoAnalysis", "system": "true", "value": "true"} in final_properties
    
    def test_case_property_workflow(self):
        """Test case property filtering workflow."""
        filter_obj = PropertyFilter()
        
        case_properties = [
            {"key": "color", "value": "red"},
            {"key": "component", "value": "TestModule"},
            {"key": "issue", "value": "ISSUE-123"},
            {"key": "__rp_case_description", "value": "Test case for component X"},
            {"key": "__rp_internal_tag", "value": "should be filtered"}
        ]
        
        case_result = filter_obj.filter_case_properties(case_properties)

        # Should keep non-RP properties
        expected_props = [
            {"key": "color", "value": "red"},
            {"key": "component", "value": "TestModule"},
            {"key": "issue", "value": "ISSUE-123"}
        ]
        
        assert len(case_result.properties) == 3
        for prop in expected_props:
            assert prop in case_result.properties

        assert case_result.description == "Test case for component X"