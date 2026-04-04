from __future__ import annotations

from weather_study_cli.application.aws_cli import extend_aws_cli_command_with_profile


def test_extend_aws_cli_command_skips_profile_when_none() -> None:
    command = ["aws", "s3", "sync", "a", "b"]
    extend_aws_cli_command_with_profile(command, None)
    assert command == ["aws", "s3", "sync", "a", "b"]


def test_extend_aws_cli_command_skips_profile_when_blank() -> None:
    command = ["aws", "s3", "sync", "a", "b"]
    extend_aws_cli_command_with_profile(command, "   ")
    assert command == ["aws", "s3", "sync", "a", "b"]


def test_extend_aws_cli_command_appends_named_profile() -> None:
    command = ["aws", "s3", "sync", "a", "b"]
    extend_aws_cli_command_with_profile(command, "dev")
    assert command == ["aws", "s3", "sync", "a", "b", "--profile", "dev"]
