"""Horaires d'ouverture d'une pharmacie : validation et statut (ouvert / ferme à / ouvre à)."""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_SHORT = {"mon": "Lun", "tue": "Mar", "wed": "Mer", "thu": "Jeu", "fri": "Ven", "sat": "Sam", "sun": "Dim"}
DAY_LONG = {"mon": "lundi", "tue": "mardi", "wed": "mercredi", "thu": "jeudi", "fri": "vendredi", "sat": "samedi", "sun": "dimanche"}
TZ = ZoneInfo("Africa/Conakry")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def clean_hours(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise {"enabled", "days"} ; ValueError si un horaire n'est pas au format HH:MM."""
    days = {}
    for key in DAY_KEYS:
        d = (raw.get("days") or {}).get(key) or {}
        open_, close = str(d.get("open") or "08:00"), str(d.get("close") or "20:00")
        if not _TIME_RE.match(open_) or not _TIME_RE.match(close):
            raise ValueError(f"Horaire invalide pour {DAY_LONG[key]} (format HH:MM attendu)")
        days[key] = {"open": open_, "close": close, "closed": bool(d.get("closed", False))}
    return {"enabled": bool(raw.get("enabled", True)), "days": days}


def _fr(t: str) -> str:
    return t.replace(":", "h")


def hours_groups(hours: Dict[str, Any]) -> List[Dict[str, str]]:
    """Regroupe les jours consécutifs ayant les mêmes horaires : [{"days": "Lun – Sam", "hours": "08h00 – 20h00"}, ...]."""
    groups: List[Dict[str, Any]] = []
    for key in DAY_KEYS:
        d = hours["days"][key]
        label = "Fermé" if d["closed"] else f"{_fr(d['open'])} – {_fr(d['close'])}"
        if groups and groups[-1]["hours"] == label:
            groups[-1]["end"] = key
        else:
            groups.append({"start": key, "end": key, "hours": label})
    return [
        {"days": DAY_SHORT[g["start"]] if g["start"] == g["end"] else f"{DAY_SHORT[g['start']]} – {DAY_SHORT[g['end']]}", "hours": g["hours"]}
        for g in groups
    ]


def hours_status(hours: Optional[Dict[str, Any]], on_duty: bool = False, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Statut public : is_open_now, status_label (« Ferme à 20h00 » / « Ouvre demain à 08h00 »), groupes d'horaires."""
    if not hours or not hours.get("enabled"):
        return {"is_open_now": None, "status_label": None, "hours_groups": [], "on_duty": bool(on_duty)}
    now = now or datetime.now(TZ)
    today = hours["days"][DAY_KEYS[now.weekday()]]
    current = now.strftime("%H:%M")
    if on_duty:
        return {"is_open_now": True, "status_label": "De garde — ouverte 24h/24", "hours_groups": hours_groups(hours), "on_duty": True}
    if not today["closed"] and today["open"] <= current < today["close"]:
        return {"is_open_now": True, "status_label": f"Ferme à {_fr(today['close'])}", "hours_groups": hours_groups(hours), "on_duty": False}
    if not today["closed"] and current < today["open"]:
        return {"is_open_now": False, "status_label": f"Ouvre à {_fr(today['open'])}", "hours_groups": hours_groups(hours), "on_duty": False}
    for offset in range(1, 8):
        day = hours["days"][DAY_KEYS[(now + timedelta(days=offset)).weekday()]]
        if not day["closed"]:
            when = "demain" if offset == 1 else DAY_LONG[DAY_KEYS[(now + timedelta(days=offset)).weekday()]]
            return {"is_open_now": False, "status_label": f"Ouvre {when} à {_fr(day['open'])}", "hours_groups": hours_groups(hours), "on_duty": False}
    return {"is_open_now": False, "status_label": "Fermée", "hours_groups": hours_groups(hours), "on_duty": False}
