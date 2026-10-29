"""
ETL Pipeline for Superstore BI Dashboard.
Extracts data from Excel or CSV, cleans, validates, transforms,
and loads into an indexed SQLite database with safe rerun support.
Also exports a Power BI-compatible dataset.
"""

import os
import sys
import time
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

# Configure Logging
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "etl.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ETLPipeline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DESKTOP_PATH = Path(r"C:\Users\HOME-LAP\Desktop\Sample - Superstore.csv")
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "superstore_bi.db"
CLEANED_DATA_PATH = DATA_DIR / "cleaned_superstore.csv"
SAMPLE_PREVIEW_PATH = DATA_DIR / "sample_superstore_preview.csv"


class ETLPipeline:
    """End-to-End ETL Pipeline for BI Dashboard."""

    def __init__(
        self,
        source_path: Optional[str] = None,
        db_path: Optional[Path] = None,
    ):
        self.source_path = self._resolve_source_path(source_path)
        self.db_path = Path(db_path) if db_path else DATABASE_PATH
        self.raw_data: Optional[pd.DataFrame] = None
        self.transformed_data: Optional[pd.DataFrame] = None
        self.metrics: Dict[str, Any] = {}

    def _resolve_source_path(self, override_path: Optional[str]) -> Path:
        """Find the valid source dataset file."""
        if override_path:
            try:
                p = Path(override_path)
                if p.is_file():
                    return p
            except (PermissionError, OSError):
                pass

        candidates = [
            DEFAULT_DESKTOP_PATH,
            Path.home() / "Desktop" / "Sample - Superstore.csv",
            Path.home() / "Desktop" / "Sample - Superstore.xlsx",
            Path.home() / "Desktop" / "Sample - Superstore.xls",
            CLEANED_DATA_PATH,
            DATA_DIR / "Sample - Superstore.csv",
            DATA_DIR / "Sample - Superstore.xlsx",
            SAMPLE_PREVIEW_PATH,
        ]

        for cand in candidates:
            try:
                if cand.exists() and cand.is_file():
                    logger.info(f"Resolved dataset location: {cand}")
                    return cand
            except (PermissionError, OSError):
                continue

        # Fallback to sample preview or Desktop path if none accessible
        if SAMPLE_PREVIEW_PATH.exists():
            return SAMPLE_PREVIEW_PATH
        return DEFAULT_DESKTOP_PATH

    def extract(self) -> pd.DataFrame:
        """Extract data from CSV or Excel with robust encoding detection."""
        start_time = time.time()
        logger.info(f"Beginning Extraction from: {self.source_path}")

        if not self.source_path.exists():
            raise FileNotFoundError(
                f"Source file not found at: {self.source_path}. "
                f"Please ensure your Superstore dataset is located on your Desktop or specified directly."
            )

        suffix = self.source_path.suffix.lower()
        df = None

        if suffix in [".xlsx", ".xls"]:
            logger.info("Extracting from Excel file...")
            excel_file = pd.ExcelFile(self.source_path)
            sheet_names = excel_file.sheet_names
            logger.info(f"Detected Excel Sheets: {sheet_names}")
            # Superstore typically uses 'Orders' or the first sheet
            target_sheet = "Orders" if "Orders" in sheet_names else sheet_names[0]
            df = pd.read_excel(excel_file, sheet_name=target_sheet)
            self.metrics["worksheet"] = target_sheet
        elif suffix == ".csv":
            encodings = ["windows-1252", "utf-8", "latin1", "cp1252", "iso-8859-1"]
            for enc in encodings:
                try:
                    logger.info(f"Attempting CSV read with encoding '{enc}'...")
                    df = pd.read_csv(self.source_path, encoding=enc)
                    self.metrics["encoding"] = enc
                    logger.info(f"Successfully loaded CSV with encoding '{enc}'")
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                raise ValueError(f"Failed to read CSV with supported encodings from {self.source_path}")
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Expected .csv or .xlsx/.xls")

        extract_duration = time.time() - start_time
        self.metrics["raw_rows"] = len(df)
        self.metrics["raw_cols"] = len(df.columns)
        self.metrics["extract_duration_seconds"] = round(extract_duration, 4)
        logger.info(f"Extracted {len(df):,} records, {len(df.columns)} columns in {extract_duration:.2f}s")
        self.raw_data = df
        return df

    def transform(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Clean, validate, and transform the raw Superstore dataset."""
        if df is None:
            if self.raw_data is None:
                df = self.extract()
            else:
                df = self.raw_data.copy()
        else:
            df = df.copy()

        start_time = time.time()
        logger.info("Beginning Data Cleaning and Validation...")

        # 1. Standardize column names (strip spaces)
        df.columns = [str(c).strip() for c in df.columns]

        # 2. Check required core columns
        expected_cols = [
            "Order ID", "Order Date", "Ship Date", "Customer ID", "Customer Name",
            "Segment", "City", "State", "Region", "Category", "Sub-Category",
            "Product ID", "Product Name", "Sales", "Quantity", "Discount", "Profit"
        ]
        missing_core = [col for col in expected_cols if col not in df.columns]
        if missing_core:
            raise ValueError(f"Missing mandatory Superstore columns: {missing_core}")

        # 3. Clean string columns (trim whitespace)
        str_cols = df.select_dtypes(include=["object", "string"]).columns
        for c in str_cols:
            df[c] = df[c].astype(str).str.strip()

        # 4. Handle duplicates
        initial_count = len(df)
        # Deduplicate based on Row ID if present, otherwise full row
        if "Row ID" in df.columns:
            df = df.drop_duplicates(subset=["Row ID"])
        else:
            df = df.drop_duplicates()
        duplicates_removed = initial_count - len(df)
        logger.info(f"Deduplication: {duplicates_removed} duplicate records removed.")

        # 5. Missing values treatment & data type validation
        # Postal code to string / clean format
        if "Postal Code" in df.columns:
            df["Postal Code"] = df["Postal Code"].replace("nan", np.nan).fillna("00000")
            df["Postal Code"] = df["Postal Code"].astype(str).str.split(".").str[0].str.zfill(5)
        else:
            df["Postal Code"] = "00000"

        # Drop records with null or corrupted critical fields
        critical_fields = ["Order ID", "Order Date", "Sales", "Quantity", "Profit"]
        df = df.dropna(subset=critical_fields)

        # 6. Parse Dates safely
        for date_col in ["Order Date", "Ship Date"]:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        df = df.dropna(subset=["Order Date"])
        # If Ship Date is null, default to Order Date
        if "Ship Date" in df.columns:
            df["Ship Date"] = df["Ship Date"].fillna(df["Order Date"])
            # Ensure Ship Date >= Order Date
            invalid_ship_dates = df["Ship Date"] < df["Order Date"]
            if invalid_ship_dates.any():
                df.loc[invalid_ship_dates, "Ship Date"] = df.loc[invalid_ship_dates, "Order Date"]

        # 7. Validate and Cast Numeric Fields
        df["Sales"] = pd.to_numeric(df["Sales"], errors="coerce").fillna(0.0)
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(1).astype(int)
        df["Discount"] = pd.to_numeric(df["Discount"], errors="coerce").fillna(0.0)
        df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce").fillna(0.0)

        # Business validation: Sales and Quantity must be strictly positive
        valid_mask = (df["Sales"] > 0) & (df["Quantity"] > 0) & (df["Discount"] >= 0) & (df["Discount"] <= 1)
        rejected_count = (~valid_mask).sum()
        if rejected_count > 0:
            logger.warning(f"Filtered out {rejected_count} business rule invalid records.")
        df = df[valid_mask].copy()

        # 8. Feature Engineering / Derived Columns
        df["shipping_days"] = (df["Ship Date"] - df["Order Date"]).dt.days
        df["order_year"] = df["Order Date"].dt.year
        df["order_month"] = df["Order Date"].dt.month
        df["order_month_name"] = df["Order Date"].dt.strftime("%b")
        df["order_quarter"] = "Q" + df["Order Date"].dt.quarter.astype(str)
        df["year_month"] = df["Order Date"].dt.strftime("%Y-%m")
        df["profit_margin_pct"] = np.where(df["Sales"] > 0, np.round((df["Profit"] / df["Sales"]) * 100, 2), 0.0)
        df["unit_price"] = np.round(df["Sales"] / df["Quantity"], 2)
        df["is_profitable"] = (df["Profit"] > 0).astype(int)

        # 9. Standardize column names to clean snake_case for SQLite & DB consistency
        column_mapping = {
            "Row ID": "row_id",
            "Order ID": "order_id",
            "Order Date": "order_date",
            "Ship Date": "ship_date",
            "Ship Mode": "ship_mode",
            "Customer ID": "customer_id",
            "Customer Name": "customer_name",
            "Segment": "segment",
            "Country": "country",
            "City": "city",
            "State": "state",
            "Postal Code": "postal_code",
            "Region": "region",
            "Product ID": "product_id",
            "Category": "category",
            "Sub-Category": "sub_category",
            "Product Name": "product_name",
            "Sales": "sales",
            "Quantity": "quantity",
            "Discount": "discount",
            "Profit": "profit",
            "Shipping Days": "shipping_days",
            "Order Year": "order_year",
            "Order Month": "order_month",
            "Month Name": "order_month_name",
            "Order Quarter": "order_quarter",
            "Year-Month": "year_month",
            "Profit Margin %": "profit_margin_pct",
            "Unit Price": "unit_price",
            "Is Profitable": "is_profitable",
        }
        df = df.rename(columns=column_mapping)

        # Format datetime columns to ISO string YYYY-MM-DD for clean SQLite storage
        df["order_date_str"] = df["order_date"].dt.strftime("%Y-%m-%d")
        df["ship_date_str"] = df["ship_date"].dt.strftime("%Y-%m-%d")

        # Row ID generation if missing
        if "row_id" not in df.columns:
            df["row_id"] = range(1, len(df) + 1)

        transform_duration = time.time() - start_time
        self.metrics["clean_rows"] = len(df)
        self.metrics["duplicates_removed"] = duplicates_removed
        self.metrics["rejected_rows"] = rejected_count
        self.metrics["transform_duration_seconds"] = round(transform_duration, 4)
        logger.info(f"Transformation complete: {len(df):,} valid records ready for load.")
        self.transformed_data = df
        return df

    def load(self, df: Optional[pd.DataFrame] = None) -> int:
        """Load cleaned records into SQLite database with indexes and safe reruns."""
        if df is None:
            if self.transformed_data is None:
                df = self.transform()
            else:
                df = self.transformed_data

        start_time = time.time()
        logger.info(f"Loading data into SQLite: {self.db_path}")

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check existing count if table exists
            cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='orders'")
            table_exists = cursor.fetchone()[0] > 0
            prior_count = 0
            if table_exists:
                cursor.execute("SELECT count(*) FROM orders")
                prior_count = cursor.fetchone()[0]
                logger.info(f"Existing 'orders' table detected with {prior_count:,} records.")

            # Create table schema
            cursor.execute("DROP TABLE IF EXISTS orders_staging")
            cursor.execute("DROP TABLE IF EXISTS orders")

            create_table_sql = """
            CREATE TABLE orders (
                row_id INTEGER PRIMARY KEY,
                order_id TEXT NOT NULL,
                order_date TEXT NOT NULL,
                ship_date TEXT NOT NULL,
                ship_mode TEXT,
                customer_id TEXT NOT NULL,
                customer_name TEXT,
                segment TEXT,
                country TEXT,
                city TEXT,
                state TEXT,
                postal_code TEXT,
                region TEXT,
                product_id TEXT NOT NULL,
                category TEXT,
                sub_category TEXT,
                product_name TEXT,
                sales REAL NOT NULL,
                quantity INTEGER NOT NULL,
                discount REAL NOT NULL,
                profit REAL NOT NULL,
                shipping_days INTEGER,
                order_year INTEGER,
                order_month INTEGER,
                order_month_name TEXT,
                order_quarter TEXT,
                year_month TEXT,
                profit_margin_pct REAL,
                unit_price REAL,
                is_profitable INTEGER
            )
            """
            cursor.execute(create_table_sql)

            # Insert dataframe records using pandas to_sql
            # Convert datetime columns to strings for SQLite
            df_to_load = df.copy()
            df_to_load["order_date"] = df_to_load["order_date"].dt.strftime("%Y-%m-%d")
            df_to_load["ship_date"] = df_to_load["ship_date"].dt.strftime("%Y-%m-%d")

            # Define exact schema columns
            schema_cols = [
                "row_id", "order_id", "order_date", "ship_date", "ship_mode",
                "customer_id", "customer_name", "segment", "country", "city",
                "state", "postal_code", "region", "product_id", "category",
                "sub_category", "product_name", "sales", "quantity", "discount",
                "profit", "shipping_days", "order_year", "order_month",
                "order_month_name", "order_quarter", "year_month",
                "profit_margin_pct", "unit_price", "is_profitable"
            ]

            # Keep only schema columns in matching order
            cols_to_insert = [c for c in schema_cols if c in df_to_load.columns]
            df_to_load = df_to_load[cols_to_insert]

            df_to_load.to_sql("orders", conn, if_exists="append", index=False)

            # Create performance indexes
            logger.info("Building database indexes for fast query execution...")
            indexes = [
                "CREATE INDEX idx_orders_order_date ON orders(order_date);",
                "CREATE INDEX idx_orders_region ON orders(region);",
                "CREATE INDEX idx_orders_category ON orders(category);",
                "CREATE INDEX idx_orders_sub_category ON orders(sub_category);",
                "CREATE INDEX idx_orders_year_month ON orders(year_month);",
                "CREATE INDEX idx_orders_customer ON orders(customer_id);",
                "CREATE INDEX idx_orders_product ON orders(product_id);",
            ]
            for idx_sql in indexes:
                cursor.execute(idx_sql)

            # Maintain ETL execution metadata table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS etl_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TEXT NOT NULL,
                source_file TEXT NOT NULL,
                records_extracted INTEGER NOT NULL,
                records_loaded INTEGER NOT NULL,
                duplicates_removed INTEGER NOT NULL,
                rejected_rows INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                status TEXT NOT NULL
            )
            """)

            load_duration = time.time() - start_time
            cursor.execute("""
            INSERT INTO etl_metadata (
                run_timestamp, source_file, records_extracted, records_loaded,
                duplicates_removed, rejected_rows, duration_seconds, status
            ) VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(self.source_path),
                self.metrics.get("raw_rows", len(df)),
                len(df),
                self.metrics.get("duplicates_removed", 0),
                self.metrics.get("rejected_rows", 0),
                round(load_duration, 4),
                "SUCCESS"
            ))

            conn.commit()

            cursor.execute("SELECT count(*) FROM orders")
            final_count = cursor.fetchone()[0]
            logger.info(f"Database Load Successful! Total records in 'orders': {final_count:,}")
            self.metrics["records_loaded"] = final_count
            self.metrics["prior_count"] = prior_count
            self.metrics["load_duration_seconds"] = round(load_duration, 4)
            return final_count

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to load data into SQLite: {e}")
            raise
        finally:
            conn.close()

    def export_power_bi(self, df: Optional[pd.DataFrame] = None) -> Path:
        """Export cleaned dataset formatted for seamless Power BI consumption."""
        if df is None:
            df = self.transformed_data

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Power BI prefers readable title-cased headers and clean datetimes
        pbi_df = df.copy()
        pbi_df["order_date"] = pbi_df["order_date"].dt.strftime("%Y-%m-%d")
        pbi_df["ship_date"] = pbi_df["ship_date"].dt.strftime("%Y-%m-%d")

        display_mapping = {
            "row_id": "Row ID",
            "order_id": "Order ID",
            "order_date": "Order Date",
            "ship_date": "Ship Date",
            "ship_mode": "Ship Mode",
            "customer_id": "Customer ID",
            "customer_name": "Customer Name",
            "segment": "Segment",
            "country": "Country",
            "city": "City",
            "state": "State",
            "postal_code": "Postal Code",
            "region": "Region",
            "product_id": "Product ID",
            "category": "Category",
            "sub_category": "Sub-Category",
            "product_name": "Product Name",
            "sales": "Sales",
            "quantity": "Quantity",
            "discount": "Discount",
            "profit": "Profit",
            "shipping_days": "Shipping Days",
            "order_year": "Order Year",
            "order_month": "Order Month",
            "order_month_name": "Month Name",
            "order_quarter": "Order Quarter",
            "year_month": "Year-Month",
            "profit_margin_pct": "Profit Margin %",
            "unit_price": "Unit Price",
            "is_profitable": "Is Profitable",
        }
        cols_to_use = [c for c in display_mapping.keys() if c in pbi_df.columns]
        pbi_df = pbi_df[cols_to_use].rename(columns=display_mapping)

        pbi_df.to_csv(CLEANED_DATA_PATH, index=False, encoding="utf-8")
        logger.info(f"Exported Power BI dataset to: {CLEANED_DATA_PATH}")

        # Also create a small preview sample for GitHub & deployment fallback
        sample_df = pbi_df.head(250)
        sample_df.to_csv(SAMPLE_PREVIEW_PATH, index=False, encoding="utf-8")
        logger.info(f"Exported sample preview to: {SAMPLE_PREVIEW_PATH}")

        return CLEANED_DATA_PATH

    def run(self) -> Dict[str, Any]:
        """Execute full ETL lifecycle: Extract -> Transform -> Load -> Export."""
        total_start = time.time()
        logger.info("=== STARTING FULL ETL PIPELINE ===")

        df_raw = self.extract()
        df_clean = self.transform(df_raw)
        records_loaded = self.load(df_clean)
        self.export_power_bi(df_clean)

        total_duration = time.time() - total_start
        self.metrics["total_duration_seconds"] = round(total_duration, 4)
        self.metrics["status"] = "SUCCESS"

        logger.info(f"=== ETL COMPLETED SUCCESSFULLY IN {total_duration:.2f}s ===")
        logger.info(f"Total Rows Loaded: {records_loaded:,}")
        return self.metrics


def run_pipeline() -> Dict[str, Any]:
    """Helper function to run the ETL pipeline."""
    pipeline = ETLPipeline()
    return pipeline.run()


if __name__ == "__main__":
    results = run_pipeline()
    print("\nETL Execution Summary:")
    for k, v in results.items():
        print(f" - {k}: {v}")
