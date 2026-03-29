from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from weather_study_cli.application.errors import StudyValidationError
from weather_study_cli.application.raw_schema import CapturePathMetadata, StudyCapture


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MOCK_DATA_DIR = PACKAGE_ROOT / "mock-data" / "raw"


@dataclass(frozen=True)
class StudyDatasetSummary:
    root: Path
    captures: tuple[StudyCapture, ...]

    @property
    def file_count(self) -> int:
        return len(self.captures)

    @property
    def weather_missing_count(self) -> int:
        return sum(1 for capture in self.captures if not capture.has_weather)

    @property
    def market_missing_count(self) -> int:
        return sum(1 for capture in self.captures if not capture.has_market)

    @property
    def cities(self) -> tuple[str, ...]:
        return tuple(sorted({capture.city_key for capture in self.captures}))

    @property
    def local_dates(self) -> tuple[str, ...]:
        return tuple(sorted({capture.local_date for capture in self.captures}))

    @property
    def capture_windows(self) -> tuple[dict[str, object], ...]:
        grouped: dict[tuple[str, str], list[StudyCapture]] = {}
        for capture in self.captures:
            grouped.setdefault((capture.city_key, capture.local_date), []).append(capture)
        windows = []
        for (city_key, local_date), captures in sorted(grouped.items()):
            ordered = sorted(captures, key=lambda item: item.local_hour)
            windows.append(
                {
                    "city": city_key,
                    "local_date": local_date,
                    "hours": [capture.local_hour for capture in ordered],
                    "missing_weather_hours": [
                        capture.local_hour for capture in ordered if not capture.has_weather
                    ],
                    "missing_market_hours": [
                        capture.local_hour for capture in ordered if not capture.has_market
                    ],
                }
            )
        return tuple(windows)

    def to_dict(self) -> dict[str, object]:
        return {
            "root": str(self.root),
            "file_count": self.file_count,
            "cities": list(self.cities),
            "local_dates": list(self.local_dates),
            "weather_missing_count": self.weather_missing_count,
            "market_missing_count": self.market_missing_count,
            "capture_windows": list(self.capture_windows),
        }


def load_capture_directory(path: str | Path) -> StudyDatasetSummary:
    root = Path(path).expanduser().resolve()
    if root.is_file():
        inferred_root = infer_capture_root(root)
        captures = (load_capture_file(root, root=inferred_root),)
        return StudyDatasetSummary(root=inferred_root, captures=captures)
    if not root.exists():
        raise StudyValidationError(f"Input path does not exist: {root}")
    files = tuple(sorted(root.rglob("*.json")))
    if not files:
        raise StudyValidationError(f"No JSON raw capture files found under {root}")
    captures = tuple(load_capture_file(file_path, root=root) for file_path in files)
    return StudyDatasetSummary(root=root, captures=captures)


def load_capture_file(path: str | Path, *, root: str | Path) -> StudyCapture:
    file_path = Path(path).expanduser().resolve()
    root_path = Path(root).expanduser().resolve()
    try:
        raw_payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StudyValidationError(f"{file_path}: invalid JSON: {exc.msg}") from exc
    try:
        metadata = parse_capture_path(file_path.relative_to(root_path))
        return StudyCapture.from_dict(raw_payload, path_metadata=metadata, source_path=file_path)
    except ValueError as exc:
        raise StudyValidationError(f"{file_path}: file is outside root {root_path}") from exc
    except StudyValidationError as exc:
        raise StudyValidationError(f"{file_path}: {exc}") from exc


def build_capture_relative_path(capture: StudyCapture) -> Path:
    return Path(
        f"study_version={capture.schema_version}",
        f"city={capture.city_name}",
        f"state={capture.state_code}",
        f"local_date={capture.local_date}",
        f"local_hour={capture.local_hour:02d}",
        f"captured_at_utc={capture.captured_at_utc.replace(':', '-')}.json",
    )


def parse_capture_path(relative_path: Path) -> CapturePathMetadata:
    parts = relative_path.parts
    if len(parts) != 6:
        raise StudyValidationError(
            "Raw capture paths must use study_version/city/state/local_date/local_hour/file.json segments."
        )
    study_version = _parse_segment(parts[0], "study_version")
    city = _parse_segment(parts[1], "city")
    state = _parse_segment(parts[2], "state")
    local_date = _parse_segment(parts[3], "local_date")
    local_hour_text = _parse_segment(parts[4], "local_hour")
    try:
        local_hour = int(local_hour_text)
    except ValueError as exc:
        raise StudyValidationError("local_hour path segment must be an integer.") from exc
    filename = parts[5]
    if not filename.endswith(".json"):
        raise StudyValidationError("Raw capture files must use a .json filename.")
    captured_value = _parse_segment(filename[:-5], "captured_at_utc")
    if "T" not in captured_value:
        raise StudyValidationError("captured_at_utc filename must contain a time component.")
    date_part, time_part = captured_value.split("T", 1)
    captured_at_utc = f"{date_part}T{time_part.replace('-', ':')}"
    return CapturePathMetadata(
        study_version=study_version,
        city=city,
        state=state,
        local_date=local_date,
        local_hour=local_hour,
        captured_at_utc=captured_at_utc,
    )


def _parse_segment(segment: str, expected_key: str) -> str:
    prefix = f"{expected_key}="
    if not segment.startswith(prefix):
        raise StudyValidationError(f"Expected path segment {expected_key}=..., got {segment!r}.")
    value = segment[len(prefix) :]
    if not value:
        raise StudyValidationError(f"{expected_key} path segment must not be empty.")
    return value


def infer_capture_root(file_path: Path) -> Path:
    try:
        study_version_dir = file_path.parents[4]
        root = file_path.parents[5]
    except IndexError as exc:
        raise StudyValidationError(
            "Single-file validation requires a study_version/city/state/local_date/local_hour/file.json path."
        ) from exc
    if not study_version_dir.name.startswith("study_version="):
        raise StudyValidationError(
            "Single-file validation requires a study_version/city/state/local_date/local_hour/file.json path."
        )
    return root
