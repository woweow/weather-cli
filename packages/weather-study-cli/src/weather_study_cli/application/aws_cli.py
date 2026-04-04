from __future__ import annotations


def extend_aws_cli_command_with_profile(command: list[str], profile: str | None) -> None:
    """Append ``--profile <name>`` only when *profile* is non-empty after strip.

    When omitted or blank, the AWS CLI uses its default credential chain
    (environment variables, shared config ``[default]``, instance role, etc.).
    """
    if profile is None:
        return
    normalized = profile.strip()
    if not normalized:
        return
    command.extend(["--profile", normalized])
