"""
Unit tests for ETL pipeline.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from etl.etl_pipeline import ETLPipeline


@pytest.fixture
def sample_csv(tmp_path):
    """Create a temporary mock Superstore CSV."""
    file_path = tmp_path / "mock_superstore.csv"
    data = {
        "Row ID": [1, 2, 3, 4],
        "Order ID": ["CA-2016-1", "CA-2016-2", "CA-2016-3", "CA-2016-4"],
        "Order Date": ["11/8/2016", "11/8/2016", "6/12/2016", "10/11/2015"],
        "Ship Date": ["11/11/2016", "11/11/2016", "6/16/2016", "10/18/2015"],
        "Ship Mode": ["Second Class", "Second Class", "Second Class", "Standard Class"],
        "Customer ID": ["CG-12520", "CG-12520", "DV-13045", "SO-20335"],
        "Customer Name": ["Claire Gute", "Claire Gute", "Darrin Van", "Sean O"],
        "Segment": ["Consumer", "Consumer", "Corporate", "Consumer"],
        "Country": ["United States", "United States", "United States", "United States"],
        "City": ["Henderson", "Henderson", "Los Angeles", "Fort Lauderdale"],
        "State": ["Kentucky", "Kentucky", "California", "Florida"],
        "Postal Code": [42420, 42420, 90036, 33311],
        "Region": ["South", "South", "West", "South"],
        "Product ID": ["FUR-BO-1", "FUR-CH-1", "OFF-LA-1", "FUR-TA-1"],
        "Category": ["Furniture", "Furniture", "Office Supplies", "Furniture"],
        "Sub-Category": ["Bookcases", "Chairs", "Labels", "Tables"],
        "Product Name": ["Bookcase", "Chairs", "Labels", "Table"],
        "Sales": [261.96, 731.94, 14.62, 957.57],
        "Quantity": [2, 3, 2, 5],
        "Discount": [0.0, 0.0, 0.0, 0.45],
        "Profit": [41.91, 219.58, 6.87, -383.03],
    }
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    return file_path


def test_etl_lifecycle(sample_csv, tmp_path):
    """Test full extract -> transform -> load -> export pipeline."""
    db_path = tmp_path / "test_db.db"
    pipeline = ETLPipeline(source_path=str(sample_csv), db_path=db_path)

    # 1. Extract
    df_raw = pipeline.extract()
    assert len(df_raw) == 4
    assert "Order ID" in df_raw.columns

    # 2. Transform
    df_clean = pipeline.transform(df_raw)
    assert len(df_clean) == 4
    assert "shipping_days" in df_clean.columns
    assert "profit_margin_pct" in df_clean.columns
    assert df_clean["shipping_days"].iloc[0] == 3

    # 3. Load
    records_loaded = pipeline.load(df_clean)
    assert records_loaded == 4

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM orders")
    assert cur.fetchone()[0] == 4

    # Verify safe rerun (idempotent)
    rerun_count = pipeline.load(df_clean)
    cur.execute("SELECT count(*) FROM orders")
    assert cur.fetchone()[0] == 4
    conn.close()


def test_missing_critical_fields_filtered(tmp_path):
    """Test records with missing required fields are dropped."""
    file_path = tmp_path / "bad_data.csv"
    data = {
        "Row ID": [1, 2],
        "Order ID": ["CA-1", "CA-2"],
        "Order Date": ["11/8/2016", None],  # Null date
        "Ship Date": ["11/11/2016", "11/15/2016"],
        "Customer ID": ["C1", "C2"],
        "Customer Name": ["Alice", "Bob"],
        "Segment": ["Consumer", "Corporate"],
        "City": ["CityA", "CityB"],
        "State": ["StateA", "StateB"],
        "Region": ["West", "East"],
        "Category": ["Furniture", "Office Supplies"],
        "Sub-Category": ["Chairs", "Paper"],
        "Product ID": ["P1", "P2"],
        "Product Name": ["Chair", "Paper"],
        "Sales": [100.0, -50.0],  # Second has negative sales
        "Quantity": [1, 1],
        "Discount": [0.0, 0.0],
        "Profit": [10.0, 0.0],
    }
    pd.DataFrame(data).to_csv(file_path, index=False)
    pipeline = ETLPipeline(source_path=str(file_path), db_path=tmp_path / "test.db")
    df_raw = pipeline.extract()
    df_clean = pipeline.transform(df_raw)
    # Only row 1 should remain
    assert len(df_clean) == 1
    assert df_clean["order_id"].iloc[0] == "CA-1"
