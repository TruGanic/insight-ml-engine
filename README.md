# Organic Food Insight Engine

The **Organic Food Insight Engine** is a FastAPI-based microservice developed for a blockchain-enabled organic food traceability research project.

The service retrieves farming and transportation records for a food batch from a blockchain API, validates and processes the data, and produces customer-friendly quality insights for use in an Augmented Reality mobile application.

## Features

- Retrieves blockchain records using a batch ID
- Validates and normalises blockchain JSON responses
- Calculates transport duration and produce freshness
- Evaluates temperature and humidity against produce-specific standards
- Generates an organic quality score and grade
- Calculates cold-chain compliance and overall trust scores
- Detects missing, inconsistent, and invalid data
- Produces short customer-readable explanations
- Returns blockchain proof fields such as transaction ID, Merkle root, and invoice hash
- Provides automatic Swagger/OpenAPI documentation

## System Flow

```text
AR Mobile Application
        |
        | GET /insights/{batchId}
        v
Insight Engine
        |
        | GET /api/retailer/history/{batchId}
        v
Blockchain API
        |
        v
Validation and Data Normalisation
        |
        v
Feature Extraction and Standards-Based Scoring
        |
        v
AR-Friendly Insights JSON
```

## Technology Stack

- Python 3
- FastAPI
- Uvicorn
- Gunicorn
- Pydantic
- HTTPX
- PyYAML
- python-dateutil
- Pytest
- Nginx
- systemd

## Project Structure

```text
insight-engine/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── scoring.py
│   └── config.py
├── config/
│   └── produce_standards.yml
├── tests/
│   ├── test_scoring_unit.py
│   └── test_api_insights.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.10 or later
- Git
- Access to the blockchain API
- A valid blockchain API base URL

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/<username>/<repository-name>.git
cd <repository-name>
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux or macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
BLOCKCHAIN_API_BASE_URL=http://<blockchain-host>:<port>
REQUEST_TIMEOUT_SECONDS=8
```

Do not commit the `.env` file to Git.

A safe example file can be committed as `.env.example`:

```env
BLOCKCHAIN_API_BASE_URL=http://localhost:8080
REQUEST_TIMEOUT_SECONDS=8
```

### 5. Start the development server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The application will be available at:

```text
http://127.0.0.1:8000
```

## API Documentation

FastAPI automatically generates interactive documentation.

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Endpoints

### Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```

### Generate Batch Insights

```http
GET /insights/{batch_id}
```

Example request:

```http
GET /insights/BATCH-234560
```

Optional query parameter:

```http
GET /insights/BATCH-234560?include_raw=true
```

`include_raw=true` includes the original blockchain response for debugging. It should normally remain disabled in production.

## Example Insights Response

```json
{
  "batchId": "BATCH-234560",
  "produceType": "Organic Cabbage",
  "status": "DELIVERED",
  "summary": {
    "organicGrade": "A",
    "organicScore": 95,
    "freshnessDaysSinceHarvest": 4,
    "coldChainComplianceScore": 88,
    "overallTrustScore": 90
  },
  "transport": {
    "tempC": {
      "min": 1.2,
      "max": 3.8,
      "avg": 2.4
    },
    "humidityPct": {
      "min": 91,
      "max": 96,
      "avg": 93.5
    },
    "durationHours": 28.21,
    "flags": []
  },
  "explanations": [
    "Harvested 4 day(s) ago.",
    "Organic level recorded as 95/100.",
    "Cold-chain compliance score: 88/100.",
    "Transport conditions were within the recommended range."
  ],
  "dataQuality": {
    "missingFields": [],
    "anomalies": []
  },
  "proof": {
    "txId": "935480d9f8d9c2a8e2536288ac385052ed2ee5413bbcd009fc67f798a435ec5c",
    "merkleRoot": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
    "invoiceHash": "QmdKnPUaT1ppK5g6Km6tXgeYjBboDGNbXVQ7NB36V26Ho2"
  }
}
```

## Produce Standards Configuration

Produce-specific temperature, humidity, and transport requirements are stored in:

```text
config/produce_standards.yml
```

Example:

```yaml
default:
  tempC:
    min: 18
    max: 26
  humidityPct:
    min: 50
    max: 75
  maxTransportHours: 120

produceTypeOverrides:
  Organic Cabbage:
    tempC:
      min: 0
      max: 4
    humidityPct:
      min: 90
      max: 98
    maxTransportHours: 120
```

The values should be reviewed and replaced with verified agricultural or food-handling standards before production use.

## Scoring Method

The current implementation uses a standards-based inference approach.

### Organic Score

The organic score is obtained from the blockchain field `organicLevel`, represented on a scale from 0 to 100.

Example grading:

```text
85–100: Grade A
70–84:  Grade B
55–69:  Grade C
0–54:   Grade D
```

### Cold-Chain Compliance Score

The cold-chain score begins at 100. Penalties are applied when:

- Maximum temperature exceeds the recommended limit
- Minimum temperature falls below the recommended limit
- Maximum humidity exceeds the recommended limit
- Minimum humidity falls below the recommended limit
- Transport duration exceeds the configured maximum

### Overall Trust Score

The overall trust score combines:

- Organic score
- Cold-chain compliance score
- Missing-field penalties
- Data-anomaly penalties

The current implementation uses a weighted calculation similar to:

```text
Overall Trust Score =
    55% Organic Score
  + 45% Cold-Chain Compliance Score
  - Data Quality Penalties
```

## Data Quality Checks

The service can detect:

- Missing required fields
- Placeholder values such as `xxxxxx`
- Minimum temperature greater than maximum temperature
- Minimum humidity greater than maximum humidity
- Humidity outside the valid 0–100% range
- Pickup timestamps occurring after delivery timestamps
- Invalid or unparseable timestamps

Example anomaly values:

```text
MIN_TEMP_GT_MAX_TEMP
MIN_HUMIDITY_GT_MAX_HUMIDITY
HUMIDITY_OUT_OF_RANGE
INVALID_TRANSPORT_TIMESTAMPS
```

## Running Tests

Install the testing dependencies if they are not already included:

```bash
pip install pytest pytest-asyncio httpx
```

Run all tests:

```bash
pytest -q
```

Run a specific test file:

```bash
pytest tests/test_scoring_unit.py -q
```

The test suite should cover:

- Health endpoint availability
- Valid insight generation
- Organic score grading
- Transport duration calculation
- Temperature and humidity excursions
- Missing data
- Invalid ranges
- Invalid timestamps
- Blockchain API errors
- Non-JSON upstream responses

## Production Deployment

The recommended deployment architecture is:

```text
Client
  |
  v
Nginx
  |
  v
Gunicorn with Uvicorn Worker
  |
  v
FastAPI Insight Engine
```

### Example systemd service

Create:

```text
/etc/systemd/system/insight-engine.service
```

Example configuration:

```ini
[Unit]
Description=Organic Food Insight Engine
After=network.target

[Service]
User=insight
Group=insight
WorkingDirectory=/opt/insight-engine
EnvironmentFile=/opt/insight-engine/.env
ExecStart=/opt/insight-engine/.venv/bin/gunicorn   -k uvicorn.workers.UvicornWorker   app.main:app   --bind 127.0.0.1:8000   --workers 1   --timeout 60

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable insight-engine
sudo systemctl start insight-engine
sudo systemctl status insight-engine
```

View logs:

```bash
sudo journalctl -u insight-engine -f
```

### Example Nginx configuration

When port 80 is already used by another application, the Insight Engine can be exposed through another port, such as `8081`.

```nginx
server {
    listen 8081;
    listen [::]:8081;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Test and reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

The deployed API can then be accessed at:

```text
http://<public-ip>:8081/health
http://<public-ip>:8081/docs
http://<public-ip>:8081/insights/BATCH-234560
```

Remember to allow the selected port in both the operating-system firewall and the Oracle Cloud ingress rules.

## Updating the Deployed Application

```bash
cd /opt/insight-engine
sudo -u insight git pull

sudo -u insight -H bash -lc '
cd /opt/insight-engine &&
source .venv/bin/activate &&
pip install -r requirements.txt
'

sudo systemctl restart insight-engine
sudo systemctl status insight-engine
```

## Limitations

- Current evaluation is standards-based rather than a trained predictive ML model.
- Accuracy depends on the quality and completeness of blockchain records.
- Minimum, maximum, and average sensor values provide less information than full time-series readings.
- Produce thresholds must be validated against authoritative agricultural and food-storage standards.
- The trust score represents an analytical indicator and should not be treated as a formal organic certification.
- HTTP deployment using only a public IP does not provide transport encryption.

## Future Improvements

- Add time-series temperature and humidity analysis
- Introduce anomaly detection using Isolation Forest or a similar model
- Predict remaining shelf life using labelled historical data
- Add API authentication and rate limiting
- Add HTTPS through a registered domain
- Store generated insight records for auditing
- Add monitoring, structured logs, and performance metrics
- Expand produce-specific standards
- Add continuous integration using GitHub Actions

## Research Context

This project forms part of a blockchain and Augmented Reality solution for improving transparency in the organic food supply chain. The Insight Engine acts as the analytical layer between immutable blockchain records and the consumer-facing AR application.

## Disclaimer

The generated scores and explanations are intended for research and prototype evaluation. They do not replace laboratory testing, official organic certification, professional food-safety assessment, or regulatory inspection.

## Licence

Add the licence selected for the repository, for example:

```text
MIT License
```

## Author

Developed as part of an undergraduate research project on blockchain-enabled organic food traceability and Augmented Reality.
