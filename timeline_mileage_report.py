#!/usr/bin/env python3
"""Build daily mileage and destination summaries from Google Timeline exports."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

METERS_PER_MILE = 1609.344
DRIVING_TYPES = {
    "IN_PASSENGER_VEHICLE",
    "IN_VEHICLE",
    "DRIVING",
    "MOTORCYCLING",
}


@dataclass
class Visit:
    start: datetime | None
    end: datetime | None
    name: str
    address: str
    place_id: str


@dataclass
class Trip:
    start: datetime | None
    end: datetime | None
    activity_type: str
    distance_miles: float
    start_name: str = ""
    end_name: str = ""
    start_address: str = ""
    end_address: str = ""


@dataclass
class DaySummary:
    date: str
    total_miles: float = 0.0
    driving_miles: float = 0.0
    trip_count: int = 0
    destinations: set[str] = field(default_factory=set)
    category: str = "review"
    category_reason: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize daily mileage from Google Timeline JSON exports."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more JSON files or directories containing Google Timeline exports.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for CSV outputs. Default: output",
    )
    parser.add_argument(
        "--timezone",
        default="America/New_York",
        help="Timezone used to group trips by day. Default: America/New_York",
    )
    parser.add_argument(
        "--config",
        help="Optional JSON file for business/personal classification rules.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, dict):
        value = (
            value.get("timestamp")
            or value.get("startTimestamp")
            or value.get("endTimestamp")
            or value.get("time")
        )
    if not value or not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def safe_get(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def latlng_from_string(value: str | None) -> tuple[float, float] | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.startswith("geo:"):
        cleaned = cleaned[4:]
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", cleaned)
    if len(matches) < 2:
        return None
    try:
        return float(matches[0]), float(matches[1])
    except ValueError:
        return None


def latlng_from_object(data: dict[str, Any] | None) -> tuple[float, float] | None:
    if not data:
        return None
    for lat_key, lng_key in (
        ("latitudeE7", "longitudeE7"),
        ("latE7", "lngE7"),
        ("latitude_e7", "longitude_e7"),
    ):
        if lat_key in data and lng_key in data:
            return data[lat_key] / 1e7, data[lng_key] / 1e7
    if "latLng" in data and isinstance(data["latLng"], str):
        return latlng_from_string(data["latLng"])
    if "centerLatE7" in data and "centerLngE7" in data:
        return data["centerLatE7"] / 1e7, data["centerLngE7"] / 1e7
    return None


def haversine_meters(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1, lon1 = first
    lat2, lon2 = second
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distance_from_path(points: Iterable[tuple[float, float]]) -> float:
    total = 0.0
    previous = None
    for point in points:
        if previous is not None:
            total += haversine_meters(previous, point)
        previous = point
    return total


def extract_name_address(location: dict[str, Any] | None) -> tuple[str, str, str]:
    if not location:
        return "", "", ""
    name = location.get("name") or location.get("locationName") or ""
    address = location.get("address") or location.get("formattedAddress") or ""
    place_id = location.get("placeId") or location.get("sourcePlaceId") or ""
    return name.strip(), address.strip(), place_id.strip()


def extract_location_fields(location: dict[str, Any] | None) -> tuple[str, str, str, tuple[float, float] | None]:
    if not location:
        return "", "", "", None
    name, address, place_id = extract_name_address(location)
    point = (
        latlng_from_object(location)
        or latlng_from_object(location.get("placeLocation") if isinstance(location, dict) else None)
        or latlng_from_string(location.get("latLng") if isinstance(location, dict) else None)
    )
    return name, address, place_id, point


def format_point(point: tuple[float, float] | None) -> str:
    if point is None:
        return ""
    return f"{point[0]:.6f}, {point[1]:.6f}"


def get_point_list(activity: dict[str, Any]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for path_key in ("timelinePath", "path", "simplifiedRawPath"):
        raw_points = activity.get(path_key)
        if not isinstance(raw_points, list):
            continue
        for item in raw_points:
            if isinstance(item, dict):
                point = latlng_from_object(item)
                if point is None and isinstance(item.get("point"), str):
                    point = latlng_from_string(item.get("point"))
                if point:
                    points.append(point)
    return points


def parse_place_visit(obj: dict[str, Any]) -> Visit | None:
    visit = obj.get("placeVisit") or obj.get("visit")
    if not isinstance(visit, dict):
        return None
    location = visit.get("location") or visit.get("topCandidate") or {}
    start = (
        parse_time(visit.get("duration", {}).get("startTimestamp"))
        or parse_time(visit.get("startTime"))
        or parse_time(obj.get("startTime"))
    )
    end = (
        parse_time(visit.get("duration", {}).get("endTimestamp"))
        or parse_time(visit.get("endTime"))
        or parse_time(obj.get("endTime"))
    )
    name, address, place_id, point = extract_location_fields(location)
    if not name and point:
        name = format_point(point)
    return Visit(start=start, end=end, name=name, address=address, place_id=place_id)


def parse_activity_segment(obj: dict[str, Any]) -> Trip | None:
    activity = obj.get("activitySegment") or obj.get("activity") or obj
    if not isinstance(activity, dict):
        return None
    has_activity_fields = any(
        key in activity
        for key in ("activityType", "distance", "distanceMeters", "timelinePath", "path", "simplifiedRawPath")
    )
    if not has_activity_fields:
        return None
    start = (
        parse_time(activity.get("duration", {}).get("startTimestamp"))
        or parse_time(activity.get("startTime"))
        or parse_time(obj.get("startTime"))
    )
    end = (
        parse_time(activity.get("duration", {}).get("endTimestamp"))
        or parse_time(activity.get("endTime"))
        or parse_time(obj.get("endTime"))
    )
    activity_type = (
        activity.get("activityType")
        or safe_get(activity, "activityType")
        or safe_get(activity, "topCandidate", "type")
        or "IN_PASSENGER_VEHICLE"
    )
    distance_meters = activity.get("distance")
    if distance_meters is None:
        distance_meters = safe_get(activity, "distanceMeters")
    if distance_meters is None:
        points = get_point_list(activity)
        if len(points) >= 2:
            distance_meters = distance_from_path(points)
    if distance_meters is None:
        start_loc = latlng_from_object(activity.get("startLocation"))
        end_loc = latlng_from_object(activity.get("endLocation"))
        if start_loc and end_loc:
            distance_meters = haversine_meters(start_loc, end_loc)
    if distance_meters is None:
        distance_meters = 0.0

    start_name, start_address, _, start_point = extract_location_fields(activity.get("startLocation"))
    end_name, end_address, _, end_point = extract_location_fields(activity.get("endLocation"))
    points = get_point_list(activity)
    if not start_point and points:
        start_point = points[0]
    if not end_point and points:
        end_point = points[-1]
    if not start_name and start_point:
        start_name = format_point(start_point)
    if not end_name and end_point:
        end_name = format_point(end_point)
    return Trip(
        start=start,
        end=end,
        activity_type=str(activity_type).strip() or "UNKNOWN",
        distance_miles=float(distance_meters) / METERS_PER_MILE,
        start_name=start_name,
        end_name=end_name,
        start_address=start_address,
        end_address=end_address,
    )


def collect_json_files(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for value in inputs:
        path = Path(value).expanduser()
        if path.is_file() and path.suffix.lower() == ".json":
            files.append(path)
            continue
        if path.is_dir():
            files.extend(sorted(path.rglob("*.json")))
    return sorted(set(files))


def parse_file(path: Path) -> tuple[list[Visit], list[Trip]]:
    data = load_json(path)
    visits: list[Visit] = []
    trips: list[Trip] = []

    if isinstance(data, dict) and isinstance(data.get("timelineObjects"), list):
        for item in data["timelineObjects"]:
            if not isinstance(item, dict):
                continue
            visit = parse_place_visit(item)
            trip = parse_activity_segment(item)
            if visit:
                visits.append(visit)
            if trip:
                trips.append(trip)
        return visits, trips

    if isinstance(data, dict) and isinstance(data.get("semanticSegments"), list):
        for item in data["semanticSegments"]:
            if not isinstance(item, dict):
                continue
            if "visit" in item or "placeVisit" in item:
                visit = parse_place_visit(item)
                if visit:
                    visits.append(visit)
            trip = parse_activity_segment(item)
            if trip:
                trips.append(trip)
        return visits, trips

    return visits, trips


def load_config(path: str | None) -> dict[str, list[str]]:
    if not path:
        return {}
    raw = load_json(Path(path))
    if not isinstance(raw, dict):
        raise ValueError("Config file must contain a JSON object.")
    normalized: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            normalized[key] = [str(item) for item in value]
    return normalized


def classify_day(summary: DaySummary, config: dict[str, list[str]]) -> tuple[str, str]:
    haystack = normalize_text(" | ".join(sorted(summary.destinations)))
    business_keywords = [normalize_text(x) for x in config.get("business_keywords", [])]
    personal_keywords = [normalize_text(x) for x in config.get("personal_keywords", [])]
    home_keywords = [normalize_text(x) for x in config.get("home_keywords", [])]

    matched_business = [keyword for keyword in business_keywords if keyword and keyword in haystack]
    matched_personal = [keyword for keyword in personal_keywords if keyword and keyword in haystack]
    matched_home = [keyword for keyword in home_keywords if keyword and keyword in haystack]

    if matched_business and not matched_personal:
        return "business", f"matched business keyword(s): {', '.join(matched_business)}"
    if matched_personal and not matched_business:
        return "personal", f"matched personal keyword(s): {', '.join(matched_personal)}"
    if matched_home and not matched_business:
        return "personal", f"matched home keyword(s): {', '.join(matched_home)}"
    if summary.driving_miles == 0:
        return "no-driving", "no driving segments found"
    return "review", "no clear classification rule matched"


def day_key(value: datetime | None, tz: ZoneInfo) -> str:
    if value is None:
        return "unknown-date"
    if value.tzinfo is None:
        localized = value.replace(tzinfo=tz)
    else:
        localized = value.astimezone(tz)
    return localized.date().isoformat()


def build_daily_summary(
    visits: list[Visit], trips: list[Trip], tz: ZoneInfo, config: dict[str, list[str]]
) -> list[DaySummary]:
    summary_by_day: dict[str, DaySummary] = {}

    for trip in trips:
        key = day_key(trip.start or trip.end, tz)
        summary = summary_by_day.setdefault(key, DaySummary(date=key))
        summary.total_miles += trip.distance_miles
        summary.trip_count += 1
        if trip.activity_type.upper() in DRIVING_TYPES:
            summary.driving_miles += trip.distance_miles
        for label in (trip.end_name, trip.end_address, trip.start_name, trip.start_address):
            if label:
                summary.destinations.add(label)

    for visit in visits:
        key = day_key(visit.start or visit.end, tz)
        summary = summary_by_day.setdefault(key, DaySummary(date=key))
        for label in (visit.name, visit.address):
            if label:
                summary.destinations.add(label)

    results = []
    for key in sorted(summary_by_day):
        summary = summary_by_day[key]
        summary.category, summary.category_reason = classify_day(summary, config)
        results.append(summary)
    return results


def format_dt(value: datetime | None, tz: ZoneInfo) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz)
    else:
        value = value.astimezone(tz)
    return value.isoformat(timespec="seconds")


def write_daily_summary(path: Path, rows: list[DaySummary]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "date",
                "total_miles",
                "driving_miles",
                "trip_count",
                "destinations",
                "suggested_category",
                "category_reason",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.date,
                    f"{row.total_miles:.2f}",
                    f"{row.driving_miles:.2f}",
                    row.trip_count,
                    " | ".join(sorted(row.destinations)),
                    row.category,
                    row.category_reason,
                ]
            )


def write_trip_details(path: Path, rows: list[Trip], tz: ZoneInfo) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "start_time",
                "end_time",
                "activity_type",
                "distance_miles",
                "start_name",
                "start_address",
                "end_name",
                "end_address",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    format_dt(row.start, tz),
                    format_dt(row.end, tz),
                    row.activity_type,
                    f"{row.distance_miles:.2f}",
                    row.start_name,
                    row.start_address,
                    row.end_name,
                    row.end_address,
                ]
            )


def write_visit_details(path: Path, rows: list[Visit], tz: ZoneInfo) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["start_time", "end_time", "name", "address", "place_id"])
        for row in rows:
            writer.writerow(
                [
                    format_dt(row.start, tz),
                    format_dt(row.end, tz),
                    row.name,
                    row.address,
                    row.place_id,
                ]
            )


def run_report(
    inputs: list[str],
    output_dir: str = "output",
    timezone: str = "America/New_York",
    config_path: str | None = None,
) -> dict[str, Any]:
    tz = ZoneInfo(timezone)
    files = collect_json_files(inputs)
    if not files:
        raise FileNotFoundError("No JSON files found in the provided inputs.")

    config = load_config(config_path)
    visits: list[Visit] = []
    trips: list[Trip] = []

    for path in files:
        file_visits, file_trips = parse_file(path)
        visits.extend(file_visits)
        trips.extend(file_trips)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    daily_rows = build_daily_summary(visits, trips, tz, config)
    daily_summary_path = output_path / "daily_summary.csv"
    trip_details_path = output_path / "trip_details.csv"
    visit_details_path = output_path / "visit_details.csv"
    write_daily_summary(daily_summary_path, daily_rows)
    write_trip_details(
        trip_details_path,
        sorted(trips, key=lambda row: row.start or datetime.min),
        tz,
    )
    write_visit_details(
        visit_details_path,
        sorted(visits, key=lambda row: row.start or datetime.min),
        tz,
    )

    return {
        "files_processed": len(files),
        "daily_summary_path": daily_summary_path,
        "trip_details_path": trip_details_path,
        "visit_details_path": visit_details_path,
        "days_summarized": len(daily_rows),
        "trip_count": len(trips),
        "visit_count": len(visits),
    }


def main() -> int:
    args = parse_args()
    try:
        result = run_report(
            inputs=args.inputs,
            output_dir=args.output_dir,
            timezone=args.timezone,
            config_path=args.config,
        )
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(str(exc)) from exc

    print(f"Processed {result['files_processed']} JSON file(s).")
    print(f"Wrote {result['daily_summary_path']}")
    print(f"Wrote {result['trip_details_path']}")
    print(f"Wrote {result['visit_details_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
