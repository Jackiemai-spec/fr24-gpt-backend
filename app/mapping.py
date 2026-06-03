import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from fastapi import HTTPException


@dataclass(frozen=True)
class AircraftMapping:
    msn: str
    registration: str
    aircraft_type: str = ""
    operator: str = ""
    effective_from: str = ""
    effective_to: str = ""
    notes: str = ""


def _parse_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    return date.fromisoformat(value)


def find_mappings_for_msn(msn: str, start: date, end: date) -> list[AircraftMapping]:
    path = Path("data/aircraft_map.csv")
    if not path.exists():
        raise HTTPException(status_code=500, detail="Missing data/aircraft_map.csv")

    target = str(msn).strip().upper()
    matches: list[AircraftMapping] = []

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_msn = str(row.get("msn", "")).strip().upper()
            if row_msn != target:
                continue

            eff_from = _parse_date(row.get("effective_from"), date(1900, 1, 1))
            eff_to = _parse_date(row.get("effective_to"), date(2999, 12, 31))

            # Overlap test: mapping interval overlaps requested report interval.
            if eff_from <= end and eff_to >= start:
                matches.append(
                    AircraftMapping(
                        msn=row_msn,
                        registration=str(row.get("registration", "")).strip().upper(),
                        aircraft_type=str(row.get("aircraft_type", "")).strip(),
                        operator=str(row.get("operator", "")).strip(),
                        effective_from=str(row.get("effective_from", "")).strip(),
                        effective_to=str(row.get("effective_to", "")).strip(),
                        notes=str(row.get("notes", "")).strip(),
                    )
                )

    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"No registration mapping found for MSN {msn}. Add it to data/aircraft_map.csv.",
        )

    return matches
