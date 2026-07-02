from datetime import datetime, timezone
from app.scoring import (
    compute_transport_duration_hours,
    cold_chain_score,
    build_data_quality_checks,
    get_standards,
    grade_from_score,
    clamp_int,
)
from types import SimpleNamespace

STANDARDS = {
    "default": {
        "tempC": {"min": 18, "max": 26},
        "humidityPct": {"min": 50, "max": 75},
        "maxTransportHours": 120,
    },
    "produceTypeOverrides": {
        "Organic Cabbage": {
            "tempC": {"min": 0, "max": 4},
            "humidityPct": {"min": 90, "max": 98},
            "maxTransportHours": 120,
        }
    }
}


def test_duration_hours_happy_path():
    pickup = "2026-02-28T04:38:38.000Z"
    delivery = "2026-03-01T08:51:04.000Z"
    hours = compute_transport_duration_hours(pickup, delivery)
    assert hours is not None
    assert hours > 0


def test_duration_hours_invalid_when_pickup_after_delivery():
    pickup = "2026-03-02T04:38:38.000Z"
    delivery = "2026-03-01T08:51:04.000Z"
    hours = compute_transport_duration_hours(pickup, delivery)
    assert hours is None


def test_cold_chain_flags_temp_high_default():
    std = get_standards(STANDARDS, "Organic Watermelon")  # not in overrides → default
    score, flags = cold_chain_score(
        minT=24.0, maxT=28.2, minH=55, maxH=60, duration_hours=10, std=std
    )
    assert "TEMP_HIGH_EXCURSION" in flags
    assert 0 <= score <= 100


def test_cold_chain_flags_for_cabbage_strict_ranges():
    std = get_standards(STANDARDS, "Organic Cabbage")  # override ranges: 0–4C
    score, flags = cold_chain_score(
        minT=23.5, maxT=27.0, minH=50, maxH=59, duration_hours=10, std=std
    )
    # For cabbage, these temps are hugely out of range
    assert "TEMP_HIGH_EXCURSION" in flags
    assert score < 50


def test_data_quality_missing_fields():
    # Create a dummy data object with missing keys
    d = SimpleNamespace(
        batchID="BATCH-1",
        produceType=None,
        organicLevel=None,
        pickupTimeStamp=None,
        deliveryTimestamp=None,
        minTemp=None,
        maxTemp=None,
        minHumidity=None,
        maxHumidity=None,
    )
    missing, anomalies = build_data_quality_checks(d)
    assert "produceType" in missing
    assert "organicLevel" in missing
    assert len(anomalies) == 0


def test_data_quality_anomaly_min_temp_gt_max_temp():
    d = SimpleNamespace(
        batchID="BATCH-1",
        produceType="X",
        organicLevel="90",
        pickupTimeStamp="2026-02-28T04:38:38.000Z",
        deliveryTimestamp="2026-03-01T08:51:04.000Z",
        minTemp=30,
        maxTemp=20,  # invalid
        minHumidity=40,
        maxHumidity=60,
    )
    missing, anomalies = build_data_quality_checks(d)
    assert "MIN_TEMP_GT_MAX_TEMP" in anomalies


def test_grade_from_score():
    assert grade_from_score(90) == "A"
    assert grade_from_score(70) == "B"
    assert grade_from_score(55) == "C"
    assert grade_from_score(10) == "D"


def test_clamp_int():
    assert clamp_int(101) == 100
    assert clamp_int(-2) == 0
    assert clamp_int(49.6) == 50