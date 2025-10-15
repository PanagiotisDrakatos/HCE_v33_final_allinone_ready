from datetime import datetime, timezone

def to_utc_iso(ts):
    if isinstance(ts, (int, float)):
        if ts > 1e12:
            dt = datetime.fromtimestamp(ts/1000.0, tz=timezone.utc)
        else:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.isoformat()
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace('Z','+00:00')).astimezone(timezone.utc).isoformat()
        except Exception:
            return datetime.now(tz=timezone.utc).isoformat()
    return datetime.now(tz=timezone.utc).isoformat()
