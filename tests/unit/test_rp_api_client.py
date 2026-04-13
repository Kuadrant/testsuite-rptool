"""
Unit tests for ReportPortal API Client timestamp normalization.
"""

from reportportal.rp_api_client import ReportPortalAPIClient


class TestTimestampNormalization:
    """Test timestamp normalization for API format changes."""

    def test_normalize_timestamp_from_integer(self):
        """Test normalizing Unix milliseconds (old format)."""
        timestamp_ms = 1640000000000
        result = ReportPortalAPIClient.normalize_timestamp(timestamp_ms)
        assert result == 1640000000000
        assert isinstance(result, int)

    def test_normalize_timestamp_from_float(self):
        """Test normalizing Unix milliseconds as float."""
        timestamp_ms = 1640000000000.0
        result = ReportPortalAPIClient.normalize_timestamp(timestamp_ms)
        assert result == 1640000000000
        assert isinstance(result, int)

    def test_normalize_timestamp_from_iso_string(self):
        """Test normalizing ISO format string (new format)."""
        # Without timezone, assumes local time
        iso_timestamp = "2021-12-20T13:33:20"
        result = ReportPortalAPIClient.normalize_timestamp(iso_timestamp)
        # Verify it returns a valid integer timestamp
        assert isinstance(result, int)
        assert result > 0

    def test_normalize_timestamp_from_iso_string_with_z(self):
        """Test normalizing ISO format string with Z suffix."""
        # 2021-12-20 13:33:20 UTC = 1640007200000ms
        iso_timestamp = "2021-12-20T13:33:20Z"
        result = ReportPortalAPIClient.normalize_timestamp(iso_timestamp)
        assert result == 1640007200000
        assert isinstance(result, int)

    def test_normalize_timestamp_from_iso_string_with_timezone(self):
        """Test normalizing ISO format string with timezone."""
        # 2021-12-20 13:33:20 UTC = 1640007200000ms
        iso_timestamp = "2021-12-20T13:33:20+00:00"
        result = ReportPortalAPIClient.normalize_timestamp(iso_timestamp)
        assert result == 1640007200000
        assert isinstance(result, int)

    def test_normalize_timestamp_none(self):
        """Test normalizing None timestamp."""
        result = ReportPortalAPIClient.normalize_timestamp(None)
        assert result is None

    def test_normalize_timestamp_invalid_string(self):
        """Test normalizing invalid timestamp string."""
        result = ReportPortalAPIClient.normalize_timestamp("invalid")
        assert result is None

    def test_normalize_timestamps_in_dict(self):
        """Test normalizing timestamps in a dictionary."""
        client = ReportPortalAPIClient("http://example.com", "project", "token")

        data = {
            'id': 'launch-123',
            'name': 'Test Launch',
            'startTime': '2021-12-20T13:33:20+00:00',
            'endTime': 1640010000000,  # Mixed formats
            'other_field': 'value'
        }

        result = client.normalize_timestamps_in_dict(data)

        assert result['id'] == 'launch-123'
        assert result['name'] == 'Test Launch'
        assert result['startTime'] == 1640007200000  # Converted from ISO
        assert result['endTime'] == 1640010000000  # Already in milliseconds
        assert result['other_field'] == 'value'

    def test_normalize_timestamps_custom_fields(self):
        """Test normalizing custom timestamp fields."""
        client = ReportPortalAPIClient("http://example.com", "project", "token")

        data = {
            'createdAt': '2021-12-20T13:33:20+00:00',
            'updatedAt': '2021-12-20T14:33:20+00:00',
        }

        result = client.normalize_timestamps_in_dict(data, ['createdAt', 'updatedAt'])

        assert result['createdAt'] == 1640007200000
        assert result['updatedAt'] == 1640010800000

    def test_normalize_timestamps_missing_fields(self):
        """Test normalizing with missing timestamp fields."""
        client = ReportPortalAPIClient("http://example.com", "project", "token")

        data = {
            'id': 'launch-123',
            'name': 'Test Launch',
        }

        # Should not raise error if fields don't exist
        result = client.normalize_timestamps_in_dict(data)

        assert result['id'] == 'launch-123'
        assert result['name'] == 'Test Launch'
        assert 'startTime' not in result
        assert 'endTime' not in result
