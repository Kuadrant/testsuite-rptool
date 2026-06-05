"""Tests for query --show-logs functionality."""

import pytest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from reportportal.rp_query import _output_failed_logs, run_query


@pytest.fixture
def mock_client():
    """Create a mock ReportPortal API client."""
    return MagicMock()


@pytest.fixture
def items_with_failed():
    """Test items including a failed STEP."""
    return [
        {
            'id': 'item1',
            'name': 'test_login',
            'type': 'STEP',
            'status': 'PASSED',
        },
        {
            'id': 'item2',
            'name': 'test_forbidden',
            'type': 'STEP',
            'status': 'FAILED',
        },
        {
            'id': 'suite1',
            'name': 'Auth Suite',
            'type': 'SUITE',
            'status': 'FAILED',
        },
    ]


@pytest.mark.unit
class TestOutputFailedLogs:
    """Test _output_failed_logs display function."""

    def test_fetches_logs_only_for_failed_steps(self, items_with_failed, mock_client, capsys):
        mock_client.get_test_item_by_id.return_value = {'id': 'item2', 'name': 'test_forbidden'}
        mock_client.get_logs.return_value = [
            {'message': 'assert 200 == 403', 'level': 'ERROR'}
        ]

        _output_failed_logs(items_with_failed, mock_client)

        mock_client.get_logs.assert_called_once_with('item2')

    def test_prints_error_message(self, items_with_failed, mock_client, capsys):
        mock_client.get_test_item_by_id.return_value = {'id': 'item2', 'name': 'test_forbidden'}
        mock_client.get_logs.return_value = [
            {'message': 'E   assert 200 == 403\nE    +  where 200 = result.status_code', 'level': 'ERROR'}
        ]

        _output_failed_logs(items_with_failed, mock_client)

        output = capsys.readouterr().out
        assert 'test_forbidden:' in output
        assert 'assert 200 == 403' in output
        assert 'where 200 = result.status_code' in output

    def test_shows_no_logs_message_when_empty(self, items_with_failed, mock_client, capsys):
        mock_client.get_test_item_by_id.return_value = {'id': 'item2', 'name': 'test_forbidden'}
        mock_client.get_logs.return_value = []

        _output_failed_logs(items_with_failed, mock_client)

        output = capsys.readouterr().out
        assert 'test_forbidden:' in output
        assert 'no error logs found' in output

    def test_no_failures_message_when_no_failed_items(self, mock_client, capsys):
        items = [
            {'id': 'item1', 'name': 'test_login', 'type': 'STEP', 'status': 'PASSED'},
        ]

        _output_failed_logs(items, mock_client)

        mock_client.get_logs.assert_not_called()
        output = capsys.readouterr().out
        assert 'No failed tests found' in output

    def test_truncates_long_messages(self, items_with_failed, mock_client, capsys):
        long_message = 'x' * 2000
        mock_client.get_test_item_by_id.return_value = {'id': 'item2', 'name': 'test_forbidden'}
        mock_client.get_logs.return_value = [
            {'message': long_message, 'level': 'ERROR'}
        ]

        _output_failed_logs(items_with_failed, mock_client)

        output = capsys.readouterr().out
        assert '...' in output

    def test_handles_log_api_error_gracefully(self, items_with_failed, mock_client, capsys):
        mock_client.get_test_item_by_id.return_value = {'id': 'item2', 'name': 'test_forbidden'}
        mock_client.get_logs.side_effect = Exception("API error")

        _output_failed_logs(items_with_failed, mock_client)

        output = capsys.readouterr().out
        assert 'Failure Details' in output
        assert 'no error logs found' in output

    def test_multiple_failed_items(self, mock_client, capsys):
        items = [
            {'id': 'f1', 'name': 'test_a', 'type': 'STEP', 'status': 'FAILED'},
            {'id': 'f2', 'name': 'test_b', 'type': 'STEP', 'status': 'FAILED'},
        ]
        mock_client.get_test_item_by_id.side_effect = [
            {'id': 'f1', 'name': 'test_a'},
            {'id': 'f2', 'name': 'test_b'},
        ]
        mock_client.get_logs.side_effect = [
            [{'message': 'error A', 'level': 'ERROR'}],
            [{'message': 'error B', 'level': 'ERROR'}],
        ]

        _output_failed_logs(items, mock_client)

        output = capsys.readouterr().out
        assert 'test_a:' in output
        assert 'error A' in output
        assert 'test_b:' in output
        assert 'error B' in output


@pytest.mark.unit
class TestOutputFailedLogsWithRetries:
    """Test _output_failed_logs with retry items from RP item detail."""

    def test_retries_shown_as_attempts(self, mock_client, capsys):
        items = [
            {'id': 'item1', 'name': 'test_flaky', 'type': 'STEP', 'status': 'FAILED'},
        ]
        mock_client.get_test_item_by_id.side_effect = [
            # First call: detail for item1 (has retries)
            {'id': 'item1', 'retries': [{'id': 'r1'}, {'id': 'r2'}, {'id': 'r3'}]},
            # Then fetching each retry item detail
            {'id': 'r1', 'status': 'FAILED'},
            {'id': 'r2', 'status': 'FAILED'},
            {'id': 'r3', 'status': 'FAILED'},
        ]
        mock_client.get_logs.side_effect = [
            [{'message': 'first try error', 'level': 'ERROR'}],
            [{'message': 'second try error', 'level': 'ERROR'}],
            [{'message': 'third try error', 'level': 'ERROR'}],
            [{'message': 'final error', 'level': 'ERROR'}],
        ]

        _output_failed_logs(items, mock_client)

        output = capsys.readouterr().out
        assert 'test_flaky (4 attempts):' in output
        assert 'Attempt 1' in output
        assert 'first try error' in output
        assert 'Attempt 2' in output
        assert 'second try error' in output
        assert 'Attempt 3' in output
        assert 'third try error' in output
        assert 'Attempt 4' in output
        assert 'final error' in output

    def test_single_log_no_attempt_label(self, mock_client, capsys):
        items = [
            {'id': 'item1', 'name': 'test_simple', 'type': 'STEP', 'status': 'FAILED'},
        ]
        # No retries in item detail
        mock_client.get_test_item_by_id.return_value = {'id': 'item1'}
        mock_client.get_logs.return_value = [
            {'message': 'simple error', 'level': 'ERROR'},
        ]

        _output_failed_logs(items, mock_client)

        output = capsys.readouterr().out
        assert 'test_simple:' in output
        assert 'simple error' in output
        assert 'attempts' not in output
        assert 'Attempt' not in output

    def test_does_not_show_passed_items(self, mock_client, capsys):
        items = [
            {'id': 'ok1', 'name': 'test_stable', 'type': 'STEP', 'status': 'PASSED'},
        ]

        _output_failed_logs(items, mock_client)

        output = capsys.readouterr().out
        assert 'test_stable' not in output

    def test_retry_with_mixed_statuses(self, mock_client, capsys):
        """Test retries where some passed and the final attempt failed."""
        items = [
            {'id': 'item1', 'name': 'test_mixed', 'type': 'STEP', 'status': 'FAILED'},
        ]
        mock_client.get_test_item_by_id.side_effect = [
            {'id': 'item1', 'retries': [{'id': 'r1'}]},
            {'id': 'r1', 'status': 'PASSED'},
        ]
        mock_client.get_logs.return_value = [
            {'message': 'final failure', 'level': 'ERROR'},
        ]

        _output_failed_logs(items, mock_client)

        output = capsys.readouterr().out
        assert 'test_mixed (2 attempts):' in output
        assert 'Attempt 1 (PASSED):' in output
        assert 'Attempt 2 (FAILED):' in output
        assert 'final failure' in output

    def test_item_detail_fetch_fails_gracefully(self, mock_client, capsys):
        """If fetching item detail fails, fall back to simple log display."""
        items = [
            {'id': 'item1', 'name': 'test_detail_err', 'type': 'STEP', 'status': 'FAILED'},
        ]
        mock_client.get_test_item_by_id.side_effect = Exception("API down")
        mock_client.get_logs.return_value = [
            {'message': 'error msg', 'level': 'ERROR'},
        ]

        _output_failed_logs(items, mock_client)

        output = capsys.readouterr().out
        assert 'test_detail_err:' in output
        assert 'error msg' in output
        assert 'Attempt' not in output


@pytest.mark.unit
class TestRunQueryShowLogsIntegration:
    """Test that run_query applies local filters and names_only to show_logs."""

    @pytest.fixture
    def base_options(self):
        return Namespace(
            rp_url='http://rp.test',
            rp_project='proj',
            rp_token='token',
            launch_id='123',
            launch_name=None,
            log_level='INFO',
            status=None,
            name=None,
            name_regex=None,
            attribute=None,
            attribute_regex=None,
            show_attributes=False,
            names_only=False,
            show_logs=True,
            limit=None,
            test_target=None,
        )

    @pytest.fixture
    def all_items(self):
        return [
            {'id': '1', 'name': 'test_alpha', 'type': 'STEP', 'status': 'FAILED'},
            {'id': '2', 'name': 'test_beta', 'type': 'STEP', 'status': 'FAILED'},
        ]

    @patch('reportportal.rp_query.ReportPortalAPIClient')
    def test_show_logs_respects_name_regex(self, MockClient, base_options, all_items, capsys):
        base_options.name_regex = 'test_alpha'

        client = MockClient.return_value
        client.get_launch_by_id.return_value = {
            'id': '123', 'name': 'launch', 'number': 1,
            'startTime': 1000, 'statistics': {'executions': {}, 'defects': {}},
        }
        client.get_test_items.return_value = all_items
        client.get_test_item_by_id.return_value = {'id': '1', 'name': 'test_alpha'}
        client.get_logs.return_value = [{'message': 'alpha error', 'level': 'ERROR'}]

        run_query(base_options)

        output = capsys.readouterr().out
        assert 'alpha error' in output
        assert 'test_beta' not in output.split('Failure Details')[-1]

    @patch('reportportal.rp_query.ReportPortalAPIClient')
    def test_show_logs_suppressed_with_names_only(self, MockClient, base_options, all_items, capsys):
        base_options.names_only = True

        client = MockClient.return_value
        client.get_test_items.return_value = all_items

        run_query(base_options)

        output = capsys.readouterr().out
        assert 'Failure Details' not in output
        client.get_logs.assert_not_called()
