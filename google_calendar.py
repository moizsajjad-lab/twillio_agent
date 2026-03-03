import json
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

from dateutil.parser import isoparse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


@dataclass(frozen=True)
class CalendarConfig:
    calendar_id: str
    service_account_file: Optional[str] = None
    service_account_json: Optional[str] = None


def load_calendar_config() -> CalendarConfig:
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "").strip()
    if not calendar_id:
        raise ValueError("Missing GOOGLE_CALENDAR_ID")

    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if service_account_file:
        service_account_file = service_account_file.strip()
    if service_account_json:
        service_account_json = service_account_json.strip()

    if not service_account_file and not service_account_json:
        raise ValueError(
            "Missing Google credentials. Set GOOGLE_SERVICE_ACCOUNT_FILE (path to JSON) "
            "or GOOGLE_SERVICE_ACCOUNT_JSON (raw JSON string)."
        )

    return CalendarConfig(
        calendar_id=calendar_id,
        service_account_file=service_account_file or None,
        service_account_json=service_account_json or None,
    )


def _build_credentials(cfg: CalendarConfig):
    if cfg.service_account_file:
        return service_account.Credentials.from_service_account_file(
            cfg.service_account_file, scopes=GOOGLE_CALENDAR_SCOPES
        )

    assert cfg.service_account_json
    info = json.loads(cfg.service_account_json)
    return service_account.Credentials.from_service_account_info(
        info, scopes=GOOGLE_CALENDAR_SCOPES
    )


def get_calendar_service(cfg: Optional[CalendarConfig] = None):
    cfg = cfg or load_calendar_config()
    creds = _build_credentials(cfg)
    return build("calendar", "v3", credentials=creds, cache_discovery=False), cfg


def _ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "data": data}


def _err(message: str, *, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"ok": False, "error": message}
    if details:
        payload["details"] = details
    return payload


def list_events(
    *,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    q: Optional[str] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    time_min/time_max must be RFC3339 timestamps (e.g. '2026-03-03T10:00:00-05:00').
    """
    try:
        service, cfg = get_calendar_service()
        resp = (
            service.events()
            .list(
                calendarId=cfg.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                q=q,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        items = []
        for e in resp.get("items", []):
            start = e.get("start", {})
            end = e.get("end", {})
            items.append(
                {
                    "id": e.get("id"),
                    "summary": e.get("summary"),
                    "description": e.get("description"),
                    "start": start.get("dateTime") or start.get("date"),
                    "end": end.get("dateTime") or end.get("date"),
                    "htmlLink": e.get("htmlLink"),
                    "status": e.get("status"),
                }
            )

        return _ok({"events": items})
    except HttpError as e:
        return _err("Google Calendar API error while listing events", details={"raw": str(e)})
    except Exception as e:
        return _err("Unexpected error while listing events", details={"raw": str(e)})


def create_event(
    *,
    summary: str,
    start: str,
    end: Optional[str] = None,
    duration_minutes: int = 60,
    timezone: str,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    start/end must be RFC3339 timestamps. If end is omitted, duration_minutes is used.
    timezone should be an IANA TZ name (e.g. 'America/New_York').
    attendees is a list of emails.
    """
    try:
        service, cfg = get_calendar_service()

        if duration_minutes <= 0:
            return _err("duration_minutes must be a positive integer")

        if not end:
            start_dt = isoparse(start)
            if start_dt.tzinfo is None:
                return _err("start must include a timezone offset (RFC3339), e.g. 2026-03-03T14:30:00-05:00")
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            end = end_dt.isoformat()

        event: Dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": timezone},
            "end": {"dateTime": end, "timeZone": timezone},
        }
        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendees:
            event["attendees"] = [{"email": e} for e in attendees]

        created = (
            service.events()
            .insert(calendarId=cfg.calendar_id, body=event, sendUpdates="all")
            .execute()
        )

        return _ok(
            {
                "id": created.get("id"),
                "htmlLink": created.get("htmlLink"),
                "summary": created.get("summary"),
                "start": (created.get("start", {}) or {}).get("dateTime"),
                "end": (created.get("end", {}) or {}).get("dateTime"),
            }
        )
    except HttpError as e:
        return _err("Google Calendar API error while creating event", details={"raw": str(e)})
    except Exception as e:
        return _err("Unexpected error while creating event", details={"raw": str(e)})


def update_event(
    *,
    event_id: str,
    summary: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    timezone: Optional[str] = None,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Patch fields on an existing event.
    If updating start/end, also pass timezone.
    """
    try:
        service, cfg = get_calendar_service()

        patch: Dict[str, Any] = {}
        if summary is not None:
            patch["summary"] = summary
        if description is not None:
            patch["description"] = description
        if location is not None:
            patch["location"] = location
        if attendees is not None:
            patch["attendees"] = [{"email": e} for e in attendees]

        if start is not None:
            if not timezone:
                return _err("timezone is required when updating start")
            patch["start"] = {"dateTime": start, "timeZone": timezone}

            if end is None and duration_minutes is not None:
                if duration_minutes <= 0:
                    return _err("duration_minutes must be a positive integer")
                start_dt = isoparse(start)
                if start_dt.tzinfo is None:
                    return _err(
                        "start must include a timezone offset (RFC3339), e.g. 2026-03-03T14:30:00-05:00"
                    )
                end_dt = start_dt + timedelta(minutes=duration_minutes)
                end = end_dt.isoformat()

        if end is not None:
            if not timezone:
                return _err("timezone is required when updating end")
            patch["end"] = {"dateTime": end, "timeZone": timezone}

        updated = (
            service.events()
            .patch(
                calendarId=cfg.calendar_id,
                eventId=event_id,
                body=patch,
                sendUpdates="all",
            )
            .execute()
        )

        return _ok(
            {
                "id": updated.get("id"),
                "htmlLink": updated.get("htmlLink"),
                "summary": updated.get("summary"),
                "start": (updated.get("start", {}) or {}).get("dateTime"),
                "end": (updated.get("end", {}) or {}).get("dateTime"),
                "status": updated.get("status"),
            }
        )
    except HttpError as e:
        return _err("Google Calendar API error while updating event", details={"raw": str(e)})
    except Exception as e:
        return _err("Unexpected error while updating event", details={"raw": str(e)})


def delete_event(*, event_id: str) -> Dict[str, Any]:
    try:
        service, cfg = get_calendar_service()
        service.events().delete(calendarId=cfg.calendar_id, eventId=event_id, sendUpdates="all").execute()
        return _ok({"deleted": True, "event_id": event_id})
    except HttpError as e:
        return _err("Google Calendar API error while deleting event", details={"raw": str(e)})
    except Exception as e:
        return _err("Unexpected error while deleting event", details={"raw": str(e)})

