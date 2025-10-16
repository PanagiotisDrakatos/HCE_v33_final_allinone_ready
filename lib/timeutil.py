from datetime import UTC, datetime


def to_utc_iso(ts):
    if isinstance(ts, (int, float)):
        if ts > 1e12:
            dt = datetime.fromtimestamp(ts / 1000.0, tz=UTC)
        else:
            dt = datetime.fromtimestamp(ts, tz=UTC)
        return dt.isoformat()
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC).isoformat()
        except Exception as e:
            # Be strict: surface invalid timestamps instead of silently substituting now()
            raise ValueError(f"Invalid ISO timestamp: {ts!r}") from e
    # Unsupported type
    raise TypeError(f"Unsupported timestamp type: {type(ts).__name__}")
