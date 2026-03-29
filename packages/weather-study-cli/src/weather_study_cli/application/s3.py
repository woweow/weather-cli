from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from weather_study_cli.application.errors import S3SyncError, StudyValidationError
from weather_study_cli.application.raw_loader import StudyDatasetSummary, load_capture_directory


DEFAULT_AWS_PROFILE = "dev"
DEFAULT_S3_PREFIX = "raw"
DEFAULT_S3_DOWNLOAD_DIR = Path(".study") / "raw-s3"


@dataclass(frozen=True)
class S3SyncSummary:
    source_uri: str
    output_root: Path
    profile: str
    delete: bool
    dry_run: bool
    validation: StudyDatasetSummary | None
    aws_output_lines: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_uri": self.source_uri,
            "output_root": str(self.output_root),
            "profile": self.profile,
            "delete": self.delete,
            "dry_run": self.dry_run,
            "aws_output_lines": list(self.aws_output_lines),
            "validation": None if self.validation is None else self.validation.to_dict(),
        }


def sync_capture_directory_from_s3(
    bucket: str,
    *,
    prefix: str = DEFAULT_S3_PREFIX,
    output_root: str | Path = DEFAULT_S3_DOWNLOAD_DIR,
    profile: str = DEFAULT_AWS_PROFILE,
    delete: bool = False,
    dry_run: bool = False,
    validate: bool = True,
) -> S3SyncSummary:
    normalized_bucket = bucket.strip()
    if not normalized_bucket:
        raise StudyValidationError("--bucket must be a non-empty S3 bucket name.")
    normalized_prefix = prefix.strip().strip("/")
    if validate and dry_run:
        raise StudyValidationError("--dry-run cannot be combined with validation.")

    source_uri = build_s3_source_uri(normalized_bucket, normalized_prefix)
    target_output_root = Path(output_root).expanduser().resolve()
    if not dry_run:
        target_output_root.mkdir(parents=True, exist_ok=True)

    command = [
        "aws",
        "s3",
        "sync",
        source_uri,
        str(target_output_root),
        "--profile",
        profile,
    ]
    if delete:
        command.append("--delete")
    if dry_run:
        command.append("--dryrun")

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown AWS CLI error"
        raise S3SyncError(f"`aws s3 sync` failed for {source_uri}: {detail}")

    validation = load_capture_directory(target_output_root) if validate else None
    output_lines = tuple(
        line
        for line in (completed.stdout.splitlines() + completed.stderr.splitlines())
        if line.strip()
    )
    return S3SyncSummary(
        source_uri=source_uri,
        output_root=target_output_root,
        profile=profile,
        delete=delete,
        dry_run=dry_run,
        validation=validation,
        aws_output_lines=output_lines,
    )


def build_s3_source_uri(bucket: str, prefix: str) -> str:
    if prefix:
        return f"s3://{bucket}/{prefix}/"
    return f"s3://{bucket}/"
