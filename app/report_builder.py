from __future__ import annotations

from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any
import xlsxwriter

REPORT_COLUMNS = [
    "Date",
    "From",
    "To",
    "Flight",
    "Flight Time",
    "STD",
    "ATD",
    "STA",
    "Status",
    "fr24_id",
    "Raw Takeoff UTC",
    "Raw Landing UTC",
]


def get_first(item: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        value = item.get(name)
        if value not in (None, ""):
            return value
    return ""


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError:
        return None


def seconds_to_excel_day_fraction(seconds: float | int | None) -> float | None:
    if seconds is None:
        return None
    try:
        seconds_float = float(seconds)
    except (TypeError, ValueError):
        return None
    if seconds_float < 0:
        return None
    return seconds_float / 86400.0


def time_to_excel_day_fraction(dt: datetime | None) -> float | None:
    if not dt:
        return None
    return (dt.hour * 3600 + dt.minute * 60 + dt.second) / 86400.0


def build_normalized_rows(raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in raw_items:
        takeoff_raw = get_first(item, ["datetime_takeoff", "takeoff_datetime", "actual_departure", "atd"])
        landing_raw = get_first(item, ["datetime_landed", "landing_datetime", "actual_arrival", "ata"])
        std_raw = get_first(item, ["datetime_scheduled_departure", "scheduled_departure", "std"])
        sta_raw = get_first(item, ["datetime_scheduled_arrival", "scheduled_arrival", "sta"])

        takeoff = parse_dt(takeoff_raw)
        landing = parse_dt(landing_raw)
        std = parse_dt(std_raw)
        sta = parse_dt(sta_raw)
        first_seen = parse_dt(item.get("first_seen"))

        origin = get_first(item, ["orig_iata", "orig_icao", "origin_iata", "origin_icao"])
        dest = get_first(
            item,
            [
                "dest_iata_actual",
                "dest_icao_actual",
                "destination_iata_actual",
                "destination_icao_actual",
                "dest_iata",
                "dest_icao",
                "destination_iata",
                "destination_icao",
            ],
        )

        duration_fraction = seconds_to_excel_day_fraction(item.get("flight_time"))
        if duration_fraction is None and takeoff and landing:
            duration_fraction = seconds_to_excel_day_fraction((landing - takeoff).total_seconds())

        report_date = (takeoff or first_seen or landing)
        status = "Landed" if item.get("flight_ended") in (True, "true", "True", 1) else ""
        if takeoff and not landing:
            status = "In flight / not landed"

        rows.append(
            {
                "Date": report_date.date() if report_date else None,
                "From": origin or "",
                "To": dest or "",
                "Flight": item.get("flight") or "",
                "Flight Time": duration_fraction,
                "STD": time_to_excel_day_fraction(std),
                "ATD": time_to_excel_day_fraction(takeoff),
                "STA": time_to_excel_day_fraction(sta),
                "Status": status,
                "fr24_id": item.get("fr24_id") or "",
                "Raw Takeoff UTC": takeoff_raw or "",
                "Raw Landing UTC": landing_raw or "",
            }
        )
    return rows


def create_xlsx_report(
    path: Path,
    *,
    msn: str | None,
    registrations: list[str],
    start_date: date,
    end_date: date,
    rows: list[dict[str, Any]],
    mapping_notes: list[str] | None = None,
) -> None:
    workbook = xlsxwriter.Workbook(str(path))

    header_fmt = workbook.add_format({"bold": True, "font_color": "white", "bg_color": "#1F4E78", "border": 1})
    date_fmt = workbook.add_format({"num_format": "yyyy-mm-dd"})
    time_fmt = workbook.add_format({"num_format": "hh:mm"})
    duration_fmt = workbook.add_format({"num_format": "[h]:mm"})
    text_fmt = workbook.add_format({"num_format": "@"})
    number_fmt = workbook.add_format({"num_format": "#,##0"})

    ws = workbook.add_worksheet("Flight_Report")
    ws.freeze_panes(1, 0)
    for col, header in enumerate(REPORT_COLUMNS):
        ws.write(0, col, header, header_fmt)

    for r, row in enumerate(rows, start=1):
        for c, header in enumerate(REPORT_COLUMNS):
            value = row.get(header)
            if header == "Date" and value:
                ws.write_datetime(r, c, datetime.combine(value, datetime.min.time()), date_fmt)
            elif header in ("STD", "ATD", "STA") and value is not None:
                ws.write_number(r, c, value, time_fmt)
            elif header == "Flight Time" and value is not None:
                ws.write_number(r, c, value, duration_fmt)
            else:
                ws.write(r, c, value if value is not None else "", text_fmt)

    ws.autofilter(0, 0, max(len(rows), 1), len(REPORT_COLUMNS) - 1)
    ws.set_column("A:A", 12)
    ws.set_column("B:C", 10)
    ws.set_column("D:D", 12)
    ws.set_column("E:E", 12)
    ws.set_column("F:H", 9)
    ws.set_column("I:I", 18)
    ws.set_column("J:J", 14)
    ws.set_column("K:L", 22)

    summary = workbook.add_worksheet("Summary")
    summary.write("A1", "FR24 Aircraft Report", header_fmt)
    summary.write("A3", "MSN")
    summary.write("B3", msn or "")
    summary.write("A4", "Registration(s)")
    summary.write("B4", ", ".join(registrations))
    summary.write("A5", "Report Start")
    summary.write_datetime("B5", datetime.combine(start_date, datetime.min.time()), date_fmt)
    summary.write("A6", "Report End")
    summary.write_datetime("B6", datetime.combine(end_date, datetime.min.time()), date_fmt)
    summary.write("A7", "Total Flights")
    summary.write_number("B7", len(rows), number_fmt)
    summary.write("A8", "Total Flight Hours")
    total_hours = sum((row.get("Flight Time") or 0) * 24 for row in rows)
    summary.write_number("B8", total_hours, workbook.add_format({"num_format": "#,##0.0"}))

    summary.write("A10", "Notes", header_fmt)
    notes = mapping_notes or []
    notes.append("Times are UTC unless you add a local-time conversion layer.")
    notes.append("Scheduled STD/STA remain blank where FR24 API response does not provide scheduled fields.")
    for idx, note in enumerate(notes, start=11):
        summary.write(idx - 1, 0, note)
    summary.set_column("A:A", 24)
    summary.set_column("B:B", 40)

    workbook.close()
