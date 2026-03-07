from fastapi import FastAPI, HTTPException
import httpx
from datetime import datetime, timezone
import json

from app.config import Settings, load_produce_standards
from app.models import BlockchainHistoryResponse, InsightsResponse, SummaryOut, TransportOut, TempHumidityRange, DataQualityOut, ProofOut
from app.scoring import (
    _to_float, get_standards, compute_transport_duration_hours,
    cold_chain_score, build_data_quality_checks, _days_since,
    clamp_int, grade_from_score, compute_overall_trust, build_explanations
)

app = FastAPI(title="Organic Food Insight Engine", version="1.0.0")

settings = Settings()
standards_cfg = load_produce_standards()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/insights/{batch_id}", response_model=InsightsResponse)
async def get_insights(batch_id: str, include_raw: bool = False):
    url = f"{settings.blockchain_api_base_url}/api/retailer/history/{batch_id}"

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            r = await client.get(url)
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="Batch not found in blockchain history API")
            r.raise_for_status()
            payload = json.loads(r)[0]
            # payload = payload_list[0]
            # payload = '{"txId":"935480d9f8d9c2a8e2536288ac385052ed2ee5413bbcd009fc67f798a435ec5c","blockTimestamp":{"seconds":1772441464,"nanos":100000000},"isDelete":false,"data":{"batchID":"BATCH-234560","farmerId":"OF12345678","harvestedDate":"2026-02-28T16:14:33.000Z","organicLevel":"95","plantedDate":"2025-12-01T08:20:14.000Z","status":"DELIVERED","produceType":"Organic Cabbage","farmerName":"Saman Fernando","supplierId":"Sup-003","transporterId":"ad4f9780-814f-4867-a388-fd786d0447ef","pickupLocation":"Embilipitiya Farm","weightKg":"1000.5","invoiceHash":"QmdKnPUaT1ppK5g6Km6tXgeYjBboDGNbXVQ7NB36V26Ho2","notes":"Handled with care","pickupTimeStamp":"2026-02-28T04:38:38.000Z","deliveryTimestamp":"2026-03-01T08:51:04.000Z","syncTimestamp":"2026-03-01T08:51:04.000Z","minTemp":24.5,"maxTemp":28.2,"avgTemp":26,"minHumidity":51,"maxHumidity":61,"avgHumidity":55.5,"merkleRoot":"8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"},"blockTimestampLK":"03/01/2026, 02:21:04 PM"}'
            # payload_json = json.loads(payload)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Blockchain API timed out")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Blockchain API error: {str(e)}")

    # Validate structure
    try:
        bh = BlockchainHistoryResponse.model_validate(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid blockchain response schema: {str(e)}")

    d = bh.data

    # Coerce numeric strings
    organic_level = _to_float(d.organicLevel)
    weight_kg = _to_float(d.weightKg)

    # Derived
    now = datetime.now(timezone.utc)
    freshness_days = _days_since(d.harvestedDate, now)
    duration_hours = compute_transport_duration_hours(d.pickupTimeStamp, d.deliveryTimestamp)

    # Data quality
    missing, anomalies = build_data_quality_checks(d)

    # Standards by produceType
    std = get_standards(standards_cfg, d.produceType)

    # Cold-chain score
    minT = _to_float(d.minTemp); maxT = _to_float(d.maxTemp); avgT = _to_float(d.avgTemp)
    minH = _to_float(d.minHumidity); maxH = _to_float(d.maxHumidity); avgH = _to_float(d.avgHumidity)

    cold_score, flags = cold_chain_score(minT, maxT, minH, maxH, duration_hours, std)

    # Organic score + grade
    organic_score = clamp_int(organic_level) if organic_level is not None else None
    organic_grade = grade_from_score(organic_score)

    # Overall trust
    trust = compute_overall_trust(
        organic_score=organic_score,
        cold_chain=cold_score,
        data_quality_missing=len(missing),
        data_quality_anom=len(anomalies),
    )

    explanations = build_explanations(
        now=now,
        produce_type=d.produceType,
        freshness_days=freshness_days,
        organic_score=organic_score,
        cold_chain=cold_score,
        flags=flags,
        std=std
    )

    resp = InsightsResponse(
        batchId=d.batchID,
        produceType=d.produceType,
        status=d.status,
        summary=SummaryOut(
            organicGrade=organic_grade,
            organicScore=organic_score,
            freshnessDaysSinceHarvest=freshness_days,
            coldChainComplianceScore=cold_score,
            overallTrustScore=trust
        ),
        transport=TransportOut(
            tempC=TempHumidityRange(min=minT, max=maxT, avg=avgT),
            humidityPct=TempHumidityRange(min=minH, max=maxH, avg=avgH),
            durationHours=duration_hours,
            flags=flags
        ),
        explanations=explanations,
        dataQuality=DataQualityOut(missingFields=missing, anomalies=anomalies),
        proof=ProofOut(txId=bh.txId, merkleRoot=d.merkleRoot, invoiceHash=d.invoiceHash),
        raw=payload if include_raw else None
    )
    return resp