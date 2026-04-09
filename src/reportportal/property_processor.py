"""
Property processing utilities for ReportPortal integration.

This module handles filtering and processing of test properties,
including ReportPortal-specific metadata extraction.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from loguru import logger

from .property_enums import ReportPortalProperties


@dataclass
class CasePropertyResult:
    """Result of filtering test case properties."""
    properties: List[Dict[str, str]] = field(default_factory=list)
    description: Optional[str] = None
    reruns: int = 0
    rerun_messages: List[str] = field(default_factory=list)
    rerun_outputs: List[str] = field(default_factory=list)


class PropertyFilter:
    """
    Handles filtering and processing of test properties for ReportPortal.
    
    This class separates ReportPortal-specific properties from regular
    test attributes and extracts description metadata.
    """
    
    def filter_suite_properties(self, properties: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], Optional[str], Optional[str]]:
        """
        Filter suite properties and extract ReportPortal metadata.
        
        Args:
            properties: List of property dictionaries
            
        Returns:
            Tuple of (filtered_properties, suite_description, launch_description)
        """
        filtered_properties = []
        suite_description = None
        launch_description = None
        
        # Handle None or empty input
        if not properties:
            return filtered_properties, suite_description, launch_description
        
        for prop in properties:
            key = prop.get('key')
            value = prop.get('value')
            
            if key == ReportPortalProperties.LAUNCH_DESCRIPTION.value:
                launch_description = value
                logger.debug("Extracted launch description from suite properties")
                
            elif key == ReportPortalProperties.SUITE_DESCRIPTION.value:
                suite_description = value
                logger.debug("Extracted suite description from suite properties")
                
            elif not ReportPortalProperties.is_rp_property(key):
                # Keep non-RP properties as regular attributes
                filtered_properties.append(prop)
            else:
                # Log other RP properties that are being filtered out
                logger.debug(f"Filtering out RP property: {key}")
        
        return filtered_properties, suite_description, launch_description
    
    def filter_case_properties(self, properties: List[Dict[str, str]]) -> CasePropertyResult:
        """
        Filter test case properties and extract description metadata.

        Args:
            properties: List of property dictionaries

        Returns:
            CasePropertyResult with filtered properties, description, and rerun info
        """
        result = CasePropertyResult()

        # Handle None or empty input
        if not properties:
            return result

        for prop in properties:
            key = prop.get('key')
            value = prop.get('value')

            if key == ReportPortalProperties.CASE_DESCRIPTION.value:
                result.description = value
                logger.debug("Extracted case description from test properties")

            elif key == ReportPortalProperties.RERUNS.value:
                try:
                    result.reruns = max(0, int(value))
                except (TypeError, ValueError):
                    logger.warning(f"Invalid rerun count value: {value!r}. Defaulting to 0.")
                    result.reruns = 0
                logger.debug(f"Extracted rerun count: {result.reruns}")

            elif key and key.startswith('__rp_rerun_') and key.endswith('_message'):
                result.rerun_messages.append(value or "")
                logger.debug(f"Extracted rerun message: {key}")

            elif key and key.startswith('__rp_rerun_') and key.endswith('_output'):
                result.rerun_outputs.append(value or "")
                logger.debug(f"Extracted rerun output: {key}")

            elif not ReportPortalProperties.is_rp_property(key):
                # Keep non-RP properties as regular attributes
                result.properties.append(prop)
            else:
                # Log other RP properties that are being filtered out
                logger.debug(f"Filtering out RP property: {key}")

        return result
    
    def promote_info_collector_properties(self, suite_name: str, suite_properties: List[Dict[str, str]], 
                                        launch_description: Optional[str]) -> Tuple[Optional[List[Dict[str, str]]], Optional[str]]:
        """
        Promote properties from info-collector suite to launch level.
        
        Args:
            suite_name: Name of the test suite
            suite_properties: Suite-level properties
            launch_description: Launch description from suite
            
        Returns:
            Tuple of (launch_properties, final_launch_description)
        """
        if suite_name == 'info-collector':
            logger.info("Promoting info-collector properties to launch level")
            return suite_properties, launch_description
        
        return None, None


class LaunchPropertyBuilder:
    """
    Builds final launch properties including auto-analysis settings.
    """
    
    def build_final_launch_properties(self, base_properties: Optional[List[Dict[str, str]]] = None, 
                                     trigger_auto_analysis: bool = False) -> List[Dict[str, str]]:
        """
        Build final launch properties with optional auto-analysis settings.
        
        Args:
            base_properties: Base properties to include
            trigger_auto_analysis: Whether to include auto-analysis properties
            
        Returns:
            List of final launch properties
        """
        final_properties = list(base_properties) if base_properties else []
        
        # Add auto-analysis properties if enabled
        if trigger_auto_analysis:
            auto_analysis_props = [
                {"key": "auto_analyze", "system": "true", "value": "true"},
                {"key": "immediateAutoAnalysis", "system": "true", "value": "true"}
            ]
            
            final_properties.extend(auto_analysis_props)
            logger.debug("Added auto-analysis properties to launch")
        else:
            logger.debug("Auto-analysis properties not added (trigger_auto_analysis=False)")
        
        return final_properties


def create_property_processor() -> PropertyFilter:
    """
    Factory function to create a PropertyFilter instance.
    
    Returns:
        Configured PropertyFilter instance
    """
    return PropertyFilter()