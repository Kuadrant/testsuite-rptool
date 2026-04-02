from enum import Enum
from typing import List


class ReportPortalProperties(Enum):
    """ReportPortal-specific property keys for metadata processing."""
    
    PREFIX = '__rp_'
    LAUNCH_PREFIX = '__rp_launch'
    SUITE_PREFIX = '__rp_suite'
    LAUNCH_DESCRIPTION = '__rp_launch_description'
    SUITE_DESCRIPTION = '__rp_suite_description'
    CASE_DESCRIPTION = '__rp_case_description'
    RERUNS = '__rp_reruns'
    
    @classmethod
    def is_rp_property(cls, key: str) -> bool:
        """Check if a property key is ReportPortal-specific."""
        return key.startswith(cls.PREFIX.value)
    
    @classmethod
    def get_description_keys(cls) -> List[str]:
        """Get all description property keys."""
        return [
            cls.LAUNCH_DESCRIPTION.value,
            cls.SUITE_DESCRIPTION.value,
            cls.CASE_DESCRIPTION.value
        ]


class MetadataProperties(Enum):
    """Standard test metadata property keys for test classification and reporting."""
    
    ISSUE = 'issue'        # Issue tracker ID (e.g., 'JIRA-123', 'ISSUE-456')
    ENV = 'env'            # Environment name (e.g., 'staging', 'production')
    OS = 'os'              # OpenShift version (e.g., 'ocp-4.18', 'ocp-4.20')
    PLATFORM = 'platform'  # Platform type: onprem, aws, rosa, aro, aws-osd, gcp-osd, gcp
    VERSION = 'version'     # Product version (e.g., '1.3.0', '1.3.0-rc1')
    BUILD = 'build'        # Build type: kuadrant, rhcl
    LEVEL = 'level'        # Testing level (e.g., 'release', 'nightly', 'smoke')


class ComponentProperties(Enum):
    """Component-specific property keys for system identification."""
    
    KUADRANT = 'kuadrant'
    DNS_OPERATOR = 'dns-operator'
    SAIL_OPERATOR = 'sail-operator'


class PlatformType(Enum):
    """Supported platform types for deployment environments."""
    
    ONPREM = 'onprem'
    AWS = 'aws'
    ROSA = 'rosa'
    ARO = 'aro'
    AWS_OSD = 'aws-osd'
    GCP_OSD = 'gcp-osd'
    GCP = 'gcp'


class BuildType(Enum):
    """Supported build types for product variants."""
    
    KUADRANT = 'kuadrant'
    RHCL = 'rhcl'


class Level(Enum):
    """Supported test levels for test categorization."""
    
    RELEASE = 'release'
    NIGHTLY = 'nightly'
    SMOKE = 'smoke'
    ACCEPTANCE = 'acceptance'
    FULLSUITE = 'fullsuite'


# Validation utility functions
def validate_platform(platform: str) -> bool:
    """Validate if platform is supported."""
    return platform in [p.value for p in PlatformType]


def validate_build_type(build: str) -> bool:
    """Validate if build type is supported."""
    return build in [b.value for b in BuildType]


def validate_test_level(level: str) -> bool:
    """Validate if test level is supported."""
    return level in [l.value for l in Level]


def get_all_metadata_keys() -> List[str]:
    """Get all standard metadata property keys."""
    return [prop.value for prop in MetadataProperties]


def get_all_component_keys() -> List[str]:
    """Get all component property keys."""
    return [prop.value for prop in ComponentProperties]


# Legacy compatibility - maintains backward compatibility
class PropertyEnum(Enum):
    """
    Legacy property enum for backward compatibility.
    
    Deprecated: Use specific property classes instead.
    - ReportPortalProperties for RP-specific keys
    - MetadataProperties for test metadata
    - ComponentProperties for component identification
    """
    
    # ReportPortal properties
    RP_PREFIX = '__rp_'
    RP_LAUNCH_PREFIX = '__rp_launch'
    RP_SUITE_PREFIX = '__rp_suite'
    RP_LAUNCH_DESCRIPTION_KEY = '__rp_launch_description'
    RP_SUITE_DESCRIPTION_KEY = '__rp_suite_description'
    RP_CASE_DESCRIPTION_KEY = '__rp_case_description'
    
    # Test metadata properties
    ISSUE = 'issue'
    ENV = 'env'
    OS = 'os'
    PLATFORM = 'platform'
    VERSION = 'version'
    BUILD = 'build'
    LEVEL = 'level'
    
    # Component properties
    KUADRANT = 'kuadrant'
    DNS_OPERATOR = 'dns-operator'
    SAIL_OPERATOR = 'sail-operator'
