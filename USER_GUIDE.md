# User Guide: Korean Semiconductors Alpha Engine

## 1. Introduction

Welcome to the Korean Semiconductors Alpha Engine! This project is a comprehensive, production-ready starter kit for building a quantitative trading system. It's designed to predict the 20-day excess returns of major Korean semiconductor stocks, like Samsung and SK hynix, against the KOSPI benchmark.

The system uses a combination of Hidden Markov Models (HMM) to identify market regimes (e.g., bull, bear, neutral) and a calibrated Elastic Net classifier to make directional predictions.

This guide will walk you through the setup, configuration, and usage of the various components of this system.

## 2. Architecture Overview

The system is designed with a modular and production-friendly architecture. The data flows through the system as follows:

```
Raw Data Sources → ETL Pipeline → Feature Store (Parquet)
                                       ↓
                    Labels ← Label Generator (20D ER)
                       ↓
           Purged CV Training → HMM + Classifier
                       ↓
              Model Artifacts (MLflow)
                       ↓
         Daily Scoring → Prediction Store → API
                       ↓
              Backtest Engine → Reports
```

**Key Principles:**

*   **No Lookahead Bias:** All features are calculated using data available up to the previous day (t-1).
*   **No Label Leakage:** The model is trained using Purged K-Fold Cross-Validation to prevent information from the training set leaking into the validation set.
*   **Production-Ready:** The code is modular, typed, tested, and includes logging.
*   **Schema Contracts:** All data is validated against predefined JSON schemas to ensure data quality.

## 3. Quick Start (5-Minute Demo)

This will get you up and running with the sample data included in the project.

```bash
# 1. Navigate to the project directory
cd stock_trading

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install the required dependencies
pip install -r requirements.txt

# 4. Run the unit tests to verify the installation
pytest -v

# 5. Generate features and labels from the sample data
python etl/build_features.py --use-samples
python labeling/make_labels.py --use-samples

# 6. Start the API server
uvicorn api.main:app --reload --port 8000
```

You now have the API server running at `http://localhost:8000`. You can explore the API documentation at `http://localhost:8000/docs`.

## 4. Installation

Follow these steps for a full installation:

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd stock_trading
    ```

2.  **Set up the environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up pre-commit hooks (for development):**
    ```bash
    pre-commit install
    ```

5.  **Set the PYTHONPATH:**
    ```bash
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    ```
    This is important to ensure that the Python interpreter can find the project's modules.

## 5. Configuration

All project configurations are managed in the `config/default.yaml` file. Here are some of the key parameters you can modify:

```yaml
symbols: ["005930.KS", "000660.KS"]  # Stocks to trade
horizon_days: 20                      # Prediction horizon
kelly_frac: 0.25                      # Kelly fraction for position sizing
weight_max: 0.05                      # Maximum position size
commission_bps: 2                     # Transaction cost in basis points
embargo_days: 20                      # CV embargo period
```

You can also configure the logging behavior in `config/logging.yaml`.

## 6. Usage

### 6.1. Generating Features (ETL)

The ETL (Extract, Transform, Load) pipeline is responsible for ingesting raw data and generating features.

*   **To run with sample data:**
    ```bash
    python etl/build_features.py --use-samples
    ```

*   **To run with your own data (production):**
    You will first need to implement the data ingestion logic in the `etl/ingest_*.py` files to connect to your data provider. Then, you can run:
    ```bash
    python etl/build_features.py --start-date 2020-01-01 --end-date 2025-10-24
    ```

The generated features will be stored in `data/gold/dt=YYYY-MM-DD/features.parquet`.

### 6.2. Generating Labels

This step creates the target variable for the model (20-day forward excess returns).

```bash
python labeling/make_labels.py --use-samples
```

The labels will be stored in `data/gold/dt=YYYY-MM-DD/labels.parquet`.

### 6.3. Training the Model

This script runs the full modeling pipeline:

```bash
python modeling/pipeline.py --train --use-samples
```

The training process involves:
1.  Merging features and labels.
2.  Fitting a 3-state Gaussian HMM to detect market regimes.
3.  Augmenting the feature set with the HMM state probabilities.
4.  Training an Elastic Net classifier using Purged 5-Fold Cross-Validation.
5.  Calibrating the model's predictions using Isotonic Regression.

**Note:** Model persistence (saving the trained model) is not yet implemented. You will need to modify `modeling/pipeline.py` to save the model artifacts.

### 6.4. Running the Backtest

The backtest engine simulates the trading strategy on historical data.

```bash
# This is a placeholder, as the backtest engine is not fully implemented
python backtest/engine.py --use-samples --report ./reports/sample
```

### 6.5. Using the API

The API provides access to the model's predictions.

*   **Start the API server:**
    ```bash
    uvicorn api.main:app --reload --port 8000
    ```

*   **API Endpoints:**
    *   `GET /v1/health`: Health check.
    *   `GET /v1/predict?symbol=005930.KS`: Get the latest prediction for a single stock.
    *   `GET /v1/predictions`: Get all latest predictions.
    *   `GET /v1/dates`: List the dates for which predictions are available.

You can interact with the API using `curl` or by visiting the auto-generated documentation at `http://localhost:8000/docs`.

## 7. Project Structure

Here is a brief overview of the project's directory structure:

```
/
├─ api/                  # FastAPI application
├─ backtest/             # Backtesting engine
├─ config/               # YAML configuration
├─ data_contracts/       # JSON schemas for data validation
├─ etl/                  # Data ingestion & feature engineering
├─ labeling/             # Label generation
├─ modeling/             # HMM + classifier + pipeline
├─ schedules/            # Placeholder for Airflow DAGs
├─ stores/               # Parquet-based data stores
├─ utils/                # Utility modules (calendar, CV, etc.)
├─ samples/              # Sample CSV data for testing
├─ tests/                # Unit tests
└─ data/                 # Runtime data (ignored by git)
```

## 8. Development

### Running Tests

To run the full test suite:
```bash
pytest -v
```

To run tests with coverage:
```bash
pytest --cov=. --cov-report=html
```

### Code Quality

The project uses `black` for code formatting and `ruff` for linting. You can run them manually:

```bash
make format
make lint
```

Pre-commit hooks are also configured to run these checks automatically when you commit code.

## 9. Roadmap & Future Work

This project is a starter kit and has several areas for future development:

*   **Data Provider Integration:** The `etl/ingest_*.py` files are stubs. You need to implement the logic to fetch data from your chosen data provider (e.g., Yahoo Finance, Bloomberg).
*   **Model Persistence:** The training pipeline does not yet save the trained models. This needs to be implemented, potentially using a tool like MLflow.
*   **Backtest Engine:** The backtest engine (`backtest/engine.py`) is incomplete and needs to be fully implemented.
*   **Deployment & Automation:** The project includes placeholders for Docker and Airflow, but the implementation is left as an exercise.

For a more detailed list of gaps and future work, please refer to the `IMPLEMENTATION_SUMMARY.md` file.
