from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class BlockTimestamp(BaseModel):
    seconds: int
    nanos: int

class BlockchainData(BaseModel):
    batchID: str
    farmerId: Optional[str] = None
    harvestedDate: Optional[str] = None  # keep string, parse later
    plantedDate: Optional[str] = None
    organicLevel: Optional[float] = None  # 0-100 (string in input, coerce later)
    status: Optional[str] = None
    produceType: Optional[str] = None
    farmerName: Optional[str] = None
    supplierId: Optional[str] = None
    transporterId: Optional[str] = None
    pickupLocation: Optional[str] = None
    weightKg: Optional[float] = None  # string in input, coerce later
    invoiceHash: Optional[str] = None
    notes: Optional[str] = None
    pickupTimeStamp: Optional[str] = None
    deliveryTimestamp: Optional[str] = None
    syncTimestamp: Optional[str] = None

    minTemp: Optional[float] = None
    maxTemp: Optional[float] = None
    avgTemp: Optional[float] = None
    minHumidity: Optional[float] = None
    maxHumidity: Optional[float] = None
    avgHumidity: Optional[float] = None

    merkleRoot: Optional[str] = None

class BlockchainHistoryResponse(BaseModel):
    txId: str
    blockTimestamp: BlockTimestamp
    isDelete: bool
    data: BlockchainData
    blockTimestampLK: Optional[str] = None

# ---- Output models (AR-friendly) ----

class TempHumidityRange(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    avg: Optional[float] = None

class TransportOut(BaseModel):
    tempC: TempHumidityRange
    humidityPct: TempHumidityRange
    durationHours: Optional[float] = None
    flags: List[str] = []

class SummaryOut(BaseModel):
    organicGrade: Optional[str] = None
    organicScore: Optional[int] = None
    freshnessDaysSinceHarvest: Optional[int] = None
    coldChainComplianceScore: Optional[int] = None
    overallTrustScore: Optional[int] = None

class DataQualityOut(BaseModel):
    missingFields: List[str] = []
    anomalies: List[str] = []

class ProofOut(BaseModel):
    txId: str
    merkleRoot: Optional[str] = None
    invoiceHash: Optional[str] = None

class InsightsResponse(BaseModel):
    batchId: str
    produceType: Optional[str] = None
    status: Optional[str] = None
    summary: SummaryOut
    transport: TransportOut
    explanations: List[str] = []
    dataQuality: DataQualityOut
    proof: ProofOut
    raw: Optional[Dict[str, Any]] = None  # optional for debugging (can disable in prod)