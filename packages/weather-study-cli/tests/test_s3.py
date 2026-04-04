from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from weather_study_cli.application.s3 import build_aws_s3_sync_command, sync_capture_directory_from_s3


def test_build_aws_s3_sync_command_includes_profile_when_non_empty():
    cmd = build_aws_s3_sync_command(
        source="s3://b/p/",
        destination="/tmp/out",
        profile="dev",
    )
    assert cmd == ["aws", "s3", "sync", "s3://b/p/", "/tmp/out", "--profile", "dev"]


def test_build_aws_s3_sync_command_omits_profile_when_empty_for_env_credentials():
    cmd = build_aws_s3_sync_command(
        source="s3://b/p/",
        destination="/tmp/out",
        profile="",
    )
    assert cmd == ["aws", "s3", "sync", "s3://b/p/", "/tmp/out"]
    cmd_ws = build_aws_s3_sync_command(
        source="s3://b/p/",
        destination="/tmp/out",
        profile="   ",
    )
    assert "--profile" not in cmd_ws


def test_sync_capture_directory_from_s3_runs_aws_without_profile_when_empty(tmp_path: Path):
    out = tmp_path / "raw-s3"

    def fake_run(cmd, capture_output, text, check):
        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        assert cmd[:4] == ["aws", "s3", "sync", "s3://my-bucket/raw/"]
        assert "--profile" not in cmd
        return R()

    with patch("weather_study_cli.application.s3.subprocess.run", fake_run):
        summary = sync_capture_directory_from_s3(
            "my-bucket",
            prefix="raw",
            output_root=out,
            profile="",
            validate=False,
        )
    assert summary.profile == ""
