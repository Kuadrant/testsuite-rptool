"""Unit tests for rptool attach matching and command wiring."""

from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from reportportal.ap import create_main_parser
from reportportal.rp_attach import filename_needle_from_rp_name, match_yaml_files, run_attach


@pytest.mark.unit
def test_needle_and_file_match(tmp_path: Path):
    """Parametrized RP name maps to apply+full YAML; other tests are ignored."""
    rp_name = (
        "testsuite/tests/singlecluster/authorino/identity/api_key/"
        "test_auth_credentials.py::test_custom_selector[authorizationHeader]"
    )
    assert filename_needle_from_rp_name(rp_name) == (
        "identity_api_key_test_auth_credentials_test_custom_selector(authorizationHeader)"
    )
    apply_file = tmp_path / (
        "testrun-x-identity_api_key_test_auth_credentials_test_custom_selector"
        "(authorizationHeader)-apply.yaml"
    )
    full_file = tmp_path / (
        "testrun-x-identity_api_key_test_auth_credentials_test_custom_selector"
        "(authorizationHeader)-full.yaml"
    )
    other = tmp_path / (
        "testrun-x-identity_api_key_test_auth_credentials_test_custom_selector(cookie)-full.yaml"
    )
    for path in (apply_file, full_file, other):
        path.write_text("# yaml\n")
    assert set(match_yaml_files(rp_name, tmp_path.iterdir())) == {apply_file, full_file}


@pytest.mark.unit
def test_needle_does_not_match_same_filename_in_other_package(tmp_path: Path):
    """keycloak vs api_key test_auth_credentials.py must not share YAML."""
    rp_name = (
        "testsuite/tests/singlecluster/authorino/identity/keycloak/"
        "test_auth_credentials.py::test_custom_selector[authorizationHeader]"
    )
    api_key_dump = tmp_path / (
        "testrun-x-identity_api_key_test_auth_credentials_test_custom_selector"
        "(authorizationHeader)-full.yaml"
    )
    api_key_dump.write_text("# yaml\n")
    assert match_yaml_files(rp_name, tmp_path.iterdir()) == []


@pytest.mark.unit
def test_parser_requires_launch_and_dir():
    """attach needs a launch selector and --dir."""
    with patch("reportportal.config.load_config_file", return_value={}):
        parser = create_main_parser()
        args = parser.parse_args(["attach", "--launch-name", "debug", "--dir", "debug-resources"])
        assert args.command == "attach"
        with pytest.raises(SystemExit):
            parser.parse_args(["attach", "--launch-name", "foo", "--launch-id", "abc", "--dir", "d"])


@pytest.mark.unit
def test_missing_dir_is_noop(tmp_path: Path):
    """Empty/missing dump dir must not fail the pipeline finally task."""
    args = Namespace(
        dir=str(tmp_path / "missing"),
        rp_url="https://rp.example",
        rp_project="proj",
        rp_token="token",
        launch_name="debug",
        launch_id=None,
    )
    assert run_attach(args) == 0


@pytest.mark.unit
@patch("reportportal.rp_attach.ReportPortalAPIClient")
def test_attaches_matched_files(mock_client_cls, tmp_path: Path):
    """Matched YAML is uploaded to the failed item."""
    yaml_file = tmp_path / (
        "testrun-x-identity_api_key_test_auth_credentials_test_custom_selector"
        "(authorizationHeader)-full.yaml"
    )
    yaml_file.write_text("kind: AuthPolicy\n")
    client = MagicMock()
    mock_client_cls.return_value = client
    client.get_launch_by_id.return_value = {"id": "launch-1", "uuid": "launch-uuid", "name": "debug"}
    client.get_test_items.return_value = [
        {
            "name": (
                "testsuite/tests/singlecluster/authorino/identity/api_key/"
                "test_auth_credentials.py::test_custom_selector[authorizationHeader]"
            ),
            "uuid": "item-uuid-1",
            "type": "STEP",
            "status": "FAILED",
        }
    ]
    args = Namespace(
        dir=str(tmp_path),
        rp_url="https://rp.example",
        rp_project="proj",
        rp_token="token",
        launch_name=None,
        launch_id="launch-1",
    )
    assert run_attach(args) == 0
    client.attach_file_to_item.assert_called_once_with("item-uuid-1", yaml_file, launch_uuid="launch-uuid")
