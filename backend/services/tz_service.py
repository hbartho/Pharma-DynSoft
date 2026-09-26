"""Utilitaires fuseau horaire pharmacie : toutes les bornes de journée se calculent
dans le fuseau configuré (settings.timezone), pas en UTC."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Africa/Conakry"


def get_pharmacy_tz() -> ZoneInfo:
    try:
        from database.repositories import SettingsRepository
        tz_name = SettingsRepository().get("timezone", DEFAULT_TIMEZONE)
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


def now_local(tz: ZoneInfo = None) -> datetime:
    tz = tz or get_pharmacy_tz()
    return datetime.now(timezone.utc).astimezone(tz)


def local_day_bounds(local_date=None, tz: ZoneInfo = None):
    """Bornes UTC [start, end) du jour local donné (defaut: aujourd'hui pharmacie)."""
    tz = tz or get_pharmacy_tz()
    if local_date is None:
        local_date = now_local(tz).date()
    start_local = datetime(local_date.year, local_date.month, local_date.day, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def parse_local_date(s: str):
    """Accepte 'YYYY-MM-DD' ou un ISO datetime; retourne la date locale pharmacie."""
    if not s:
        return None
    try:
        if len(s) == 10:
            return datetime.strptime(s, '%Y-%m-%d').date()
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return dt.date()
        return dt.astimezone(get_pharmacy_tz()).date()
    except (ValueError, TypeError):
        return None


def to_local_day_str(dt: datetime, tz: ZoneInfo = None) -> str:
    """Date 'YYYY-MM-DD' d'un instant, dans le fuseau pharmacie."""
    tz = tz or get_pharmacy_tz()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).strftime('%Y-%m-%d')
