import pytest
from httpx import AsyncClient, Response
from app.main import app


VALID_PAYLOAD = {
    "txId": "935480d9f8d9c2a8e2536288ac385052ed2ee5413bbcd009fc67f798a435ec5c",
    "blockTimestamp": {"seconds": 1772441464, "nanos": 100000000},
    "isDelete": False,
    "data": {
        "batchID": "BATCH-234560",
        "farmerId": "OF12345678",
        "harvestedDate": "2026-02-28T16:14:33.000Z",
        "organicLevel": "95",
        "plantedDate": "2025-12-01T08:20:14.000Z",
        "status": "DELIVERED",
        "produceType": "Organic Cabbage",
        "farmerName": "Saman Fernando",
        "supplierId": "Sup-003",
        "transporterId": "ad4f9780-814f-4867-a388-fd786d0447ef",
        "pickupLocation": "Embilipitiya Farm",
        "weightKg": "1000.5",
        "invoiceHash": "QmdKnPUaT1ppK5g6Km6tXgeYjBboDGNbXVQ7NB36V26Ho2",
        "notes": "Handled with care",
        "pickupTimeStamp": "2026-02-28T04:38:38.000Z",
        "deliveryTimestamp": "2026-03-01T08:51:04.000Z",
        "syncTimestamp": "2026-03-01T08:51:04.000Z",
        "minTemp": 24.5,
        "maxTemp": 28.2,
        "avgTemp": 26,
        "minHumidity": 51,
        "maxHumidity": 61,
        "avgHumidity": 55.5,
        "merkleRoot": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
    },
    "blockTimestampLK": "03/01/2026, 02:21:04 PM",
}


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_insights_success(monkeypatch):
    # Patch httpx.AsyncClient.get used inside your endpoint
    async def mock_get(self, url):
        return Response(200, json=VALID_PAYLOAD)

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/insights/BATCH-234560")
        assert r.status_code == 200
        body = r.json()

        assert body["batchId"] == "BATCH-234560"
        assert body["summary"]["organicScore"] == 95
        assert "overallTrustScore" in body["summary"]
        assert isinstance(body["explanations"], list)
        assert "proof" in body


@pytest.mark.asyncio
async def test_insights_blockchain_404(monkeypatch):
    async def mock_get(self, url):
        return Response(404, json={"detail": "not found"})

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/insights/BATCH-DOES-NOT-EXIST")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_insights_non_json_response(monkeypatch):
    # Simulate upstream returning HTML (like a login page)
    async def mock_get(self, url):
        return Response(200, text="<html>login</html>")

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/insights/BATCH-234560")
        assert r.status_code in (500, 502)