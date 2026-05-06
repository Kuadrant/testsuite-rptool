"""
Unit tests for reportportal_client_wrapper module.
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock

from reportportal.reportportal_client_wrapper import (
    ReportPortalClientWrapper,
    AutoAnalysisTrigger,
    create_rp_client
)


@pytest.mark.unit
class TestReportPortalClientWrapper:
    """Test ReportPortalClientWrapper class."""
    
    def test_initialization(self):
        """Test wrapper initialization."""
        wrapper = ReportPortalClientWrapper(
            url="https://example.com",
            project="test_project",
            token="test_api_key"
        )

        assert wrapper.url == "https://example.com"
        assert wrapper.project == "test_project"
        assert wrapper.token == "test_api_key"
        assert wrapper.client is None
    
    @patch('reportportal.reportportal_client_wrapper.RPClient')
    def test_start_session_success(self, mock_rp_client):
        """Test successful session start."""
        mock_client = Mock()
        mock_rp_client.return_value = mock_client
        
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.start_session()

        mock_rp_client.assert_called_once_with(
            endpoint="https://example.com",
            project="project",
            api_key="key"
        )
        mock_client.start.assert_called_once()
        assert wrapper.client == mock_client
    
    @patch('reportportal.reportportal_client_wrapper.RPClient')
    def test_start_session_failure(self, mock_rp_client):
        """Test session start failure."""
        mock_rp_client.side_effect = Exception("Connection failed")
        
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        
        with pytest.raises(Exception, match="Connection failed"):
            wrapper.start_session()
    
    def test_terminate_session_success(self):
        """Test successful session termination."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        
        wrapper.terminate_session()
        wrapper.client.terminate.assert_called_once()
    
    def test_terminate_session_no_client(self):
        """Test session termination with no client."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = None
        
        # Should not raise exception
        wrapper.terminate_session()
    
    def test_terminate_session_failure(self):
        """Test session termination failure."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        wrapper.client.terminate.side_effect = Exception("Termination failed")
        
        # Should not raise exception but log error
        wrapper.terminate_session()
        wrapper.client.terminate.assert_called_once()
    
    def test_start_launch_success(self):
        """Test successful launch start."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        wrapper.client.start_launch.return_value = "launch_123"
        
        launch_id = wrapper.start_launch(
            name="Test Launch",
            start_time="2024-01-01T12:00:00",
            description="Launch description"
        )
        
        assert launch_id == "launch_123"
        wrapper.client.start_launch.assert_called_once_with(
            name="Test Launch",
            start_time="2024-01-01T12:00:00",
            description="Launch description"
        )
    
    def test_start_launch_no_client(self):
        """Test launch start with no client session."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = None
        
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.start_launch("Test Launch", "2024-01-01T12:00:00")
    
    def test_start_launch_failure(self):
        """Test launch start failure."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        wrapper.client.start_launch.side_effect = Exception("Launch failed")
        
        with pytest.raises(Exception, match="Launch failed"):
            wrapper.start_launch("Test Launch", "2024-01-01T12:00:00")
    
    @patch('reportportal.reportportal_client_wrapper.timestamp')
    def test_finish_launch_success(self, mock_timestamp):
        """Test successful launch finish."""
        # Mock timestamp to return a known value for the end_time override
        mock_timestamp.return_value = "1234567890000"

        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        launch_info = {"id": "launch_123", "status": "PASSED"}
        wrapper.client.get_launch_info.return_value = launch_info
        
        result = wrapper.finish_launch(
            end_time="2024-01-01T13:00:00",
            attributes=[{"key": "platform", "value": "aws"}],
            description="Final description"
        )
        
        assert result == launch_info
        # The end_time is now overridden with timestamp() result
        wrapper.client.finish_launch.assert_called_once_with(
            end_time="1234567890000",
            attributes=[{"key": "platform", "value": "aws"}],
            description="Final description"
        )
    
    def test_finish_launch_no_client(self):
        """Test launch finish with no client session."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = None
        
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.finish_launch("2024-01-01T13:00:00")
    
    def test_start_test_suite_success(self):
        """Test successful test suite start."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        wrapper.client.start_test_item.return_value = "suite_456"
        
        suite_id = wrapper.start_test_suite(
            name="Test Suite",
            start_time="2024-01-01T12:00:00",
            attributes=[{"key": "component", "value": "TestComponent"}],
            description="Suite description"
        )
        
        assert suite_id == "suite_456"
        wrapper.client.start_test_item.assert_called_once_with(
            name="Test Suite",
            start_time="2024-01-01T12:00:00",
            item_type="SUITE",
            attributes=[{"key": "component", "value": "TestComponent"}],
            description="Suite description"
        )
    
    def test_start_test_suite_no_client(self):
        """Test suite start with no client session."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = None
        
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.start_test_suite("Test Suite", "2024-01-01T12:00:00")
    
    def test_finish_test_suite_success(self):
        """Test successful test suite finish."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        
        wrapper.finish_test_suite(
            suite_id="suite_456",
            end_time="2024-01-01T13:00:00",
            attributes=[{"key": "status", "value": "completed"}]
        )
        
        wrapper.client.finish_test_item.assert_called_once_with(
            item_id="suite_456",
            end_time="2024-01-01T13:00:00",
            attributes=[{"key": "status", "value": "completed"}]
        )
    
    def test_finish_test_suite_no_client(self):
        """Test suite finish with no client session."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = None
        
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.finish_test_suite("suite_456", "2024-01-01T13:00:00")
    
    def test_start_test_case_success(self):
        """Test successful test case start."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        wrapper.client.start_test_item.return_value = "case_789"
        
        case_id = wrapper.start_test_case(
            name="Test Case",
            start_time="2024-01-01T12:00:00",
            parent_id="suite_456",
            attributes=[{"key": "color", "value": "green"}],
            description="Case description"
        )
        
        assert case_id == "case_789"
        wrapper.client.start_test_item.assert_called_once_with(
            name="Test Case",
            start_time="2024-01-01T12:00:00",
            item_type="STEP",
            attributes=[{"key": "color", "value": "green"}],
            description="Case description",
            parent_item_id="suite_456",
            code_ref=None,
            test_case_id=None,
            retry=False,
            retry_of=None
        )

    def test_start_test_case_with_code_ref(self):
        """Test test case start with code_ref parameter."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        wrapper.client.start_test_item.return_value = "case_789"

        case_id = wrapper.start_test_case(
            name="Test Case",
            start_time="2024-01-01T12:00:00",
            parent_id="suite_456",
            attributes=[{"key": "color", "value": "green"}],
            description="Case description",
            code_ref="path/to/test.py::test_name"
        )

        assert case_id == "case_789"
        wrapper.client.start_test_item.assert_called_once_with(
            name="Test Case",
            start_time="2024-01-01T12:00:00",
            item_type="STEP",
            attributes=[{"key": "color", "value": "green"}],
            description="Case description",
            parent_item_id="suite_456",
            code_ref="path/to/test.py::test_name",
            test_case_id=None,
            retry=False,
            retry_of=None
        )

    def test_start_test_case_no_client(self):
        """Test case start with no client session."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = None
        
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.start_test_case("Test Case", "2024-01-01T12:00:00", "suite_456")
    
    def test_finish_test_case_success(self):
        """Test successful test case finish."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        
        wrapper.finish_test_case(
            case_id="case_789",
            end_time="2024-01-01T13:00:00",
            status="PASSED",
            attributes=[{"key": "result", "value": "success"}]
        )
        
        wrapper.client.finish_test_item.assert_called_once_with(
            item_id="case_789",
            end_time="2024-01-01T13:00:00",
            status="PASSED",
            attributes=[{"key": "result", "value": "success"}]
        )
    
    def test_finish_test_case_no_client(self):
        """Test case finish with no client session."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = None
        
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.finish_test_case("case_789", "2024-01-01T13:00:00", "PASSED")
    
    @patch('reportportal.reportportal_client_wrapper.timestamp')
    def test_log_message_success(self, mock_timestamp):
        """Test successful message logging."""
        mock_timestamp.return_value = "12345"
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        
        wrapper.log_message("item_123", "Test message", "INFO")
        
        wrapper.client.log.assert_called_once_with(
            time="12345",
            message="Test message",
            level="INFO",
            item_id="item_123"
        )
    
    def test_log_message_no_client(self):
        """Test message logging with no client."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = None
        
        # Should not raise exception
        wrapper.log_message("item_123", "Test message")
    
    def test_log_message_empty_message(self):
        """Test message logging with empty message."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        
        # Should not call client.log
        wrapper.log_message("item_123", "")
        wrapper.client.log.assert_not_called()
    
    def test_log_test_outputs_success(self):
        """Test successful test output logging."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        
        with patch.object(wrapper, 'log_message') as mock_log:
            wrapper.log_test_outputs(
                case_id="case_123",
                system_out="Standard output",
                system_err="Standard error", 
                failures=["Failure 1", "Failure 2"],
                errors=["Error 1", 'Error 2'],
                skipped=["Skip reason"]
            )
            
            # Check all log calls
            expected_calls = [
                ("case_123", "Failure 1", "ERROR"),
                ("case_123", "Failure 2", "ERROR"),
                ("case_123", "Error 1", "ERROR"),
                ("case_123", "Error 2", "ERROR"),
                ("case_123", "Skip reason", "ERROR"),
                ("case_123", "Standard output", "INFO"),
                ("case_123", "Standard error", "ERROR")
            ]
            
            assert mock_log.call_count == 7
            for expected_call in expected_calls:
                mock_log.assert_any_call(*expected_call)
    
    def test_log_test_outputs_no_outputs(self):
        """Test test output logging with no outputs."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        wrapper.client = Mock()
        
        with patch.object(wrapper, 'log_message') as mock_log:
            wrapper.log_test_outputs(
                case_id="case_123",
                system_out=None,
                system_err=None,
                failures=[],
                errors=[],
                skipped=[]
            )
            
            mock_log.assert_not_called()


@pytest.mark.unit
class TestAutoAnalysisTrigger:
    """Test AutoAnalysisTrigger class."""
    
    def test_initialization(self):
        """Test trigger initialization."""
        trigger = AutoAnalysisTrigger(
            url="https://example.com",
            project="test_project",
            token="test_api_key"
        )

        assert trigger.url == "https://example.com"
        assert trigger.project == "test_project"
        assert trigger.token == "test_api_key"
    
    @patch('reportportal.reportportal_client_wrapper.requests.post')
    def test_trigger_auto_analysis_success(self, mock_post):
        """Test successful auto-analysis trigger."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        trigger = AutoAnalysisTrigger(
            url="https://example.com",
            project="test_project",
            token="test_api_key"
        )
        
        result = trigger.trigger_auto_analysis("launch_123")
        
        assert result is True
        mock_post.assert_called_once_with(
            url="https://example.com/api/v1/test_project/launch/analyze",
            headers={
                'Authorization': 'bearer test_api_key',
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
    
    @patch('reportportal.reportportal_client_wrapper.requests.post')
    def test_trigger_auto_analysis_failure(self, mock_post):
        """Test auto-analysis trigger failure."""
        mock_post.side_effect = requests.exceptions.RequestException("Request failed")
        
        trigger = AutoAnalysisTrigger(
            url="https://example.com",
            project="test_project",
            token="test_api_key"
        )
        
        result = trigger.trigger_auto_analysis("launch_123")
        
        assert result is False
    
    @patch('reportportal.reportportal_client_wrapper.requests.post')
    def test_trigger_auto_analysis_http_error(self, mock_post):
        """Test auto-analysis trigger with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_post.return_value = mock_response
        
        trigger = AutoAnalysisTrigger(
            url="https://example.com",
            project="test_project", 
            token="test_api_key"
        )
        
        result = trigger.trigger_auto_analysis("launch_123")
        
        assert result is False


@pytest.mark.unit
class TestCreateRpClient:
    """Test create_rp_client factory function."""
    
    def test_create_rp_client(self):
        """Test client factory function."""
        client = create_rp_client(
            url="https://example.com",
            project="test_project",
            token="test_api_key"
        )
        
        assert isinstance(client, ReportPortalClientWrapper)
        assert client.url == "https://example.com"
        assert client.project == "test_project"
        assert client.token == "test_api_key"


@pytest.mark.unit
class TestReportPortalClientWrapperIntegration:
    """Integration tests for ReportPortalClientWrapper."""
    
    @patch('reportportal.reportportal_client_wrapper.timestamp')
    @patch('reportportal.reportportal_client_wrapper.RPClient')
    def test_full_test_reporting_workflow(self, mock_rp_client, mock_timestamp):
        """Test complete test reporting workflow."""
        # Mock timestamp for finish_launch end_time override
        mock_timestamp.return_value = "1234567890000"

        # Setup mock client
        mock_client = Mock()
        mock_client.start_launch.return_value = "launch_123"
        mock_client.start_test_item.side_effect = ["suite_456", "case_789"]
        mock_client.get_launch_info.return_value = {"id": "launch_123", "status": "PASSED"}
        mock_rp_client.return_value = mock_client
        
        # Create wrapper
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        
        # Start session
        wrapper.start_session()
        assert wrapper.client == mock_client
        
        # Start launch
        launch_id = wrapper.start_launch("Test Launch", "2024-01-01T12:00:00")
        assert launch_id == "launch_123"
        
        # Start test suite
        suite_id = wrapper.start_test_suite("Test Suite", "2024-01-01T12:01:00")
        assert suite_id == "suite_456"
        
        # Start test case
        case_id = wrapper.start_test_case("Test Case", "2024-01-01T12:02:00", suite_id)
        assert case_id == "case_789"
        
        # Log test outputs
        wrapper.log_test_outputs(case_id, "output", "error", ["failure"], ["error"], ["skip"])
        
        # Finish test case
        wrapper.finish_test_case(case_id, "2024-01-01T12:03:00", "FAILED")
        
        # Finish test suite
        wrapper.finish_test_suite(suite_id, "2024-01-01T12:04:00")
        
        # Finish launch
        launch_info = wrapper.finish_launch("2024-01-01T12:05:00")
        assert launch_info["id"] == "launch_123"
        
        # Terminate session
        wrapper.terminate_session()
        mock_client.terminate.assert_called_once()
        
        # Verify all client method calls
        mock_client.start.assert_called_once()
        mock_client.start_launch.assert_called_once()
        assert mock_client.start_test_item.call_count == 2
        assert mock_client.finish_test_item.call_count == 2
        mock_client.finish_launch.assert_called_once()
        mock_client.get_launch_info.assert_called_once()
    
    def test_error_handling_workflow(self):
        """Test error handling in various scenarios."""
        wrapper = ReportPortalClientWrapper("https://example.com", "project", "key")
        
        # Test operations without client session
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.start_launch("Test", "2024-01-01T12:00:00")
        
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.finish_launch("2024-01-01T12:00:00")
            
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.start_test_suite("Suite", "2024-01-01T12:00:00")
            
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.finish_test_suite("suite_id", "2024-01-01T12:00:00")
            
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.start_test_case("Case", "2024-01-01T12:00:00", "parent_id")
            
        with pytest.raises(RuntimeError, match="Client session not started"):
            wrapper.finish_test_case("case_id", "2024-01-01T12:00:00", "PASSED")