from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_ROOT = Path(__file__).resolve().parent
DIST_DIR = DEPLOY_ROOT / "dist"
ZIP_PATH = DIST_DIR / "weather-study-collector-lambda.zip"
ROLE_POLICY_NAME = "weather-study-collector-s3-write"
MANAGED_POLICY_ARN = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

PACKAGE_SOURCES = (
    REPO_ROOT / "packages" / "weather-study-collector" / "src" / "weather_study_collector",
    REPO_ROOT / "packages" / "weather-study-cli" / "src" / "weather_study_cli",
    REPO_ROOT / "packages" / "weather-cli" / "src" / "weather_cli",
    REPO_ROOT / "packages" / "kalshi-weather-markets-cli" / "src" / "kalshi_weather_markets_cli",
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    zip_path = build_lambda_zip(ZIP_PATH)
    role_arn = ensure_lambda_role(
        role_name=args.role_name,
        bucket=args.bucket,
        prefix=args.prefix,
        profile=args.profile,
    )
    deploy_lambda(
        function_name=args.function_name,
        role_arn=role_arn,
        zip_path=zip_path,
        bucket=args.bucket,
        prefix=args.prefix,
        profile=args.profile,
        region=args.region,
        contact_email=args.contact_email,
    )

    print(
        json.dumps(
            {
                "function_name": args.function_name,
                "role_name": args.role_name,
                "bucket": args.bucket,
                "prefix": args.prefix,
                "region": args.region,
                "profile": args.profile,
                "zip_path": str(zip_path),
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Package and deploy the weather study collector Lambda.",
    )
    parser.add_argument(
        "--bucket",
        required=True,
        help="S3 bucket where the Lambda will write raw study captures.",
    )
    parser.add_argument(
        "--prefix",
        default="raw",
        help="S3 prefix where the Lambda will write raw study captures (default: %(default)s)",
    )
    parser.add_argument(
        "--function-name",
        default="weather-study-collector-dev",
        help="Lambda function name (default: %(default)s)",
    )
    parser.add_argument(
        "--role-name",
        default="weather-study-collector-lambda-role",
        help="IAM role name for the Lambda function (default: %(default)s)",
    )
    parser.add_argument(
        "--profile",
        default="dev",
        help="AWS profile to use for deployment (default: %(default)s)",
    )
    parser.add_argument(
        "--region",
        default="us-west-2",
        help="AWS region for the Lambda function (default: %(default)s)",
    )
    parser.add_argument(
        "--contact-email",
        default="weather-cli@example.com",
        help="Contact email passed through to the collector for NOAA User-Agent headers.",
    )
    return parser


def build_lambda_zip(target_zip: Path) -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="weather-study-lambda-build-") as temp_dir:
        staging_root = Path(temp_dir).resolve()
        for source_dir in PACKAGE_SOURCES:
            shutil.copytree(
                source_dir,
                staging_root / source_dir.name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
        shutil.copy2(DEPLOY_ROOT / "handler.py", staging_root / "handler.py")
        with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in sorted(staging_root.rglob("*")):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(staging_root))
    return target_zip


def ensure_lambda_role(*, role_name: str, bucket: str, prefix: str, profile: str) -> str:
    existing = run_aws(
        ["iam", "get-role", "--role-name", role_name],
        profile=profile,
        region=None,
        check=False,
    )
    if existing.returncode == 0:
        role = json.loads(existing.stdout)["Role"]
        role_arn = role["Arn"]
    else:
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as trust_file:
            json.dump(trust_policy, trust_file)
            trust_path = Path(trust_file.name)
        try:
            created = run_aws(
                [
                    "iam",
                    "create-role",
                    "--role-name",
                    role_name,
                    "--assume-role-policy-document",
                    f"file://{trust_path}",
                ],
                profile=profile,
                region=None,
            )
        finally:
            trust_path.unlink(missing_ok=True)
        role_arn = json.loads(created.stdout)["Role"]["Arn"]
        time.sleep(10)

    run_aws(
        [
            "iam",
            "attach-role-policy",
            "--role-name",
            role_name,
            "--policy-arn",
            MANAGED_POLICY_ARN,
        ],
        profile=profile,
        region=None,
        check=False,
    )

    object_resource = f"arn:aws:s3:::{bucket}/{prefix.strip().strip('/') + '/' if prefix.strip().strip('/') else ''}*"
    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject"],
                "Resource": object_resource,
            }
        ],
    }
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as policy_file:
        json.dump(inline_policy, policy_file)
        policy_path = Path(policy_file.name)
    try:
        run_aws(
            [
                "iam",
                "put-role-policy",
                "--role-name",
                role_name,
                "--policy-name",
                ROLE_POLICY_NAME,
                "--policy-document",
                f"file://{policy_path}",
            ],
            profile=profile,
            region=None,
        )
    finally:
        policy_path.unlink(missing_ok=True)

    return role_arn


def deploy_lambda(
    *,
    function_name: str,
    role_arn: str,
    zip_path: Path,
    bucket: str,
    prefix: str,
    profile: str,
    region: str,
    contact_email: str,
) -> None:
    env_payload = json.dumps(
        {
            "Variables": {
                "WEATHER_STUDY_BUCKET": bucket,
                "WEATHER_STUDY_PREFIX": prefix,
                "WEATHER_STUDY_CONTACT_EMAIL": contact_email,
                "WEATHER_STUDY_COLLECTOR_NAME": "weather-market-study-lambda",
            }
        }
    )
    exists = run_aws(
        ["lambda", "get-function", "--function-name", function_name],
        profile=profile,
        region=region,
        check=False,
    )
    if exists.returncode == 0:
        run_aws(
            [
                "lambda",
                "update-function-code",
                "--function-name",
                function_name,
                "--zip-file",
                f"fileb://{zip_path}",
            ],
            profile=profile,
            region=region,
        )
        wait_for_lambda_ready(function_name=function_name, profile=profile, region=region)
        run_aws(
            [
                "lambda",
                "update-function-configuration",
                "--function-name",
                function_name,
                "--role",
                role_arn,
                "--handler",
                "handler.handler",
                "--runtime",
                "python3.12",
                "--timeout",
                "120",
                "--memory-size",
                "512",
                "--environment",
                env_payload,
            ],
            profile=profile,
            region=region,
        )
    else:
        run_aws(
            [
                "lambda",
                "create-function",
                "--function-name",
                function_name,
                "--role",
                role_arn,
                "--runtime",
                "python3.12",
                "--handler",
                "handler.handler",
                "--zip-file",
                f"fileb://{zip_path}",
                "--timeout",
                "120",
                "--memory-size",
                "512",
                "--environment",
                env_payload,
            ],
            profile=profile,
            region=region,
        )
    wait_for_lambda_ready(function_name=function_name, profile=profile, region=region)


def wait_for_lambda_ready(*, function_name: str, profile: str, region: str, timeout_seconds: int = 180) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = run_aws(
            ["lambda", "get-function-configuration", "--function-name", function_name],
            profile=profile,
            region=region,
            check=False,
        )
        if result.returncode == 0:
            payload = json.loads(result.stdout)
            state = payload.get("State")
            last_update_status = payload.get("LastUpdateStatus")
            if state == "Active" and last_update_status in {None, "Successful"}:
                return
            if state == "Failed" or last_update_status == "Failed":
                raise RuntimeError(f"Lambda {function_name} failed to become ready: {result.stdout}")
        time.sleep(5)
    raise TimeoutError(f"Timed out waiting for Lambda {function_name} to become ready.")


def run_aws(
    args: list[str],
    *,
    profile: str,
    region: str | None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = ["aws", *args, "--profile", profile]
    if region is not None:
        command.extend(["--region", region])
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown AWS CLI error"
        raise RuntimeError(f"AWS CLI command failed: {' '.join(command)}\n{detail}")
    return completed


if __name__ == "__main__":
    raise SystemExit(main())
