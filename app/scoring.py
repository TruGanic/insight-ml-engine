from datetime import datetime, timezone
from dateutil import parser as dtparser
from typing import Dict, Tuple, List, Optional
import math

def _to_float(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).strip())
    except Exception:
        return None

def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        # handles "2026-03-02T08:51:04.000Z"
        dt = dtparser.isoparse(ts)
        return dt
    except Exception:
        return None

def _days_since(date_str: Optional[str], now: datetime) -> Optional[int]:
    if not date_str or "xxxx" in date_str.lower():
        return None
    dt = _parse_iso(date_str)
    if not dt:
        # If your harvestedDate is not ISO, adjust here
        return None
    delta = now - dt
    return max(0, int(delta.total_seconds() // 86400))

def get_standards(standards_cfg: Dict, produce_type: Optional[str]) -> Dict:
    base = standards_cfg.get("default", {})
    overrides = standards_cfg.get("produceTypeOverrides", {})
    if produce_type and produce_type in overrides:
        merged = {**base, **overrides[produce_type]}
        # shallow merge works for this structure
        return merged
    return base

def compute_transport_duration_hours(pickup_ts: Optional[str], delivery_ts: Optional[str]) -> Optional[float]:
    p = _parse_iso(pickup_ts)
    d = _parse_iso(delivery_ts)
    if not p or not d:
        return None
    hours = (d - p).total_seconds() / 3600.0
    if hours < 0:
        return None
    return round(hours, 2)

def grade_from_score(score: Optional[int]) -> Optional[str]:
    if score is None:
        return None
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"

def clamp_int(x: float, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(x))))

def cold_chain_score(minT, maxT, minH, maxH, duration_hours: Optional[float], std: Dict) -> Tuple[int, List[str]]:
    flags = []
    score = 100.0

    tmin_std = std.get("tempC", {}).get("min")
    tmax_std = std.get("tempC", {}).get("max")
    hmin_std = std.get("humidityPct", {}).get("min")
    hmax_std = std.get("humidityPct", {}).get("max")
    max_transport = std.get("maxTransportHours")

    # Temp excursion penalties
    if maxT is not None and tmax_std is not None and maxT > tmax_std:
        exc = maxT - tmax_std
        score -= exc * 10
        flags.append("TEMP_HIGH_EXCURSION")

    if minT is not None and tmin_std is not None and minT < tmin_std:
        exc = tmin_std - minT
        score -= exc * 10
        flags.append("TEMP_LOW_EXCURSION")

    # Humidity penalties
    if maxH is not None and hmax_std is not None and maxH > hmax_std:
        exc = maxH - hmax_std
        score -= exc * 2
        flags.append("HUMIDITY_HIGH_EXCURSION")

    if minH is not None and hmin_std is not None and minH < hmin_std:
        exc = hmin_std - minH
        score -= exc * 2
        flags.append("HUMIDITY_LOW_EXCURSION")

    # Duration penalty
    if duration_hours is not None and max_transport is not None and duration_hours > max_transport:
        score -= (duration_hours - max_transport) * 0.2
        flags.append("TRANSPORT_TOO_LONG")

    return clamp_int(score), list(sorted(set(flags)))

def build_data_quality_checks(data) -> Tuple[List[str], List[str]]:
    missing = []
    anomalies = []

    required = [
        "batchID", "produceType", "organicLevel",
        "pickupTimeStamp", "deliveryTimestamp",
        "minTemp", "maxTemp", "minHumidity", "maxHumidity"
    ]

    for f in required:
        v = getattr(data, f, None)
        if v is None or (isinstance(v, str) and (v.strip() == "" or "xxxx" in v.lower())):
            missing.append(f)

    # basic sanity checks
    minT = _to_float(getattr(data, "minTemp", None))
    maxT = _to_float(getattr(data, "maxTemp", None))
    minH = _to_float(getattr(data, "minHumidity", None))
    maxH = _to_float(getattr(data, "maxHumidity", None))

    if minT is not None and maxT is not None and minT > maxT:
        anomalies.append("MIN_TEMP_GT_MAX_TEMP")
    if minH is not None and maxH is not None and minH > maxH:
        anomalies.append("MIN_HUMIDITY_GT_MAX_HUMIDITY")

    if minH is not None and (minH < 0 or minH > 100):
        anomalies.append("HUMIDITY_OUT_OF_RANGE")
    if maxH is not None and (maxH < 0 or maxH > 100):
        anomalies.append("HUMIDITY_OUT_OF_RANGE")

    dur = compute_transport_duration_hours(getattr(data, "pickupTimeStamp", None),
                                          getattr(data, "deliveryTimestamp", None))
    if dur is None and getattr(data, "pickupTimeStamp", None) and getattr(data, "deliveryTimestamp", None):
        anomalies.append("INVALID_TRANSPORT_TIMESTAMPS")

    return missing, anomalies

def compute_overall_trust(organic_score: Optional[int], cold_chain: Optional[int], data_quality_missing: int, data_quality_anom: int) -> Optional[int]:
    if organic_score is None and cold_chain is None:
        return None
    # Weighted average + penalties
    o = organic_score if organic_score is not None else 70
    c = cold_chain if cold_chain is not None else 70

    trust = 0.55 * o + 0.45 * c
    trust -= data_quality_missing * 3
    trust -= data_quality_anom * 5

    return clamp_int(trust)

def build_explanations(now: datetime, produce_type: Optional[str], freshness_days: Optional[int],
                       organic_score: Optional[int], cold_chain: Optional[int],
                       flags: List[str], std: Dict) -> List[str]:
    lines = []

    if freshness_days is not None:
        lines.append(f"Harvested {freshness_days} day(s) ago.")

    if organic_score is not None:
        lines.append(f"Organic level recorded as {organic_score}/100.")

    if cold_chain is not None:
        lines.append(f"Cold-chain compliance score: {cold_chain}/100.")

    # Explain flags in simple terms
    if "TEMP_HIGH_EXCURSION" in flags:
        lines.append("Temperature exceeded the recommended maximum for this produce type.")
    if "TEMP_LOW_EXCURSION" in flags:
        lines.append("Temperature dropped below the recommended minimum for this produce type.")
    if "HUMIDITY_HIGH_EXCURSION" in flags:
        lines.append("Humidity exceeded the recommended maximum range.")
    if "HUMIDITY_LOW_EXCURSION" in flags:
        lines.append("Humidity dropped below the recommended minimum range.")
    if "TRANSPORT_TOO_LONG" in flags:
        lines.append("Transport duration exceeded the recommended maximum window.")

    # If no flags, reassure
    if not flags and cold_chain is not None and cold_chain >= 85:
        lines.append("Transport conditions were within the recommended range.")

    return lines[:6]  # keep AR short