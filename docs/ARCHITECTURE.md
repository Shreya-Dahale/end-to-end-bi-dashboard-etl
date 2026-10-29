# System Architecture & Technical Design

## 1. High-Level System Architecture

```mermaid
flowchart TD
    subgraph Ingestion ["1. Data Ingestion & Extraction"]
        RawExcel["Superstore Excel / CSV Dataset<br/>(Desktop / Local Data Store)"]
        ETLExtract["ETL Extractor<br/>(Encoding Detector: UTF-8 / Windows-1252 / Latin-1)"]
        RawExcel --> ETLExtract
    end

    subgraph Processing ["2. Transformation & Validation"]
        Clean["Data Cleaning & Deduplication<br/>(Trimming, Null Handling, Type Coercion)"]
        Validate["Business Rule Validation<br/>(Sales > 0, Discount in [0,1], Ship Date >= Order Date)"]
        FeatEng["Feature Engineering<br/>(Shipping Days, Profit Margin %, Temporal Attributes)"]
        ETLExtract --> Clean --> Validate --> FeatEng
    end

    subgraph Storage ["3. Storage & Relational Layer"]
        SQLiteDB[("SQLite Database<br/>(superstore_bi.db)<br/>Indexed by Date, Region, Category")]
        PBIExport["Clean Power BI Dataset<br/>(data/cleaned_superstore.csv)"]
        AuditTable["Audit Metadata Table<br/>(etl_metadata)"]
        FeatEng --> SQLiteDB
        FeatEng --> PBIExport
        FeatEng --> AuditTable
    end

    subgraph Analytics ["4. Advanced Analytics & Modeling"]
        OLS["Trend Analysis<br/>(OLS Regression, R², Slope, p-value)"]
        Forecast["Time Series Forecasting<br/>(Holt-Winters & ARIMA / SARIMAX)"]
        WhatIf["What-If Scenario Simulation<br/>(-10% to +20% Growth Engine)"]
        SQLiteDB --> OLS
        SQLiteDB --> Forecast
        SQLiteDB --> WhatIf
    end

    subgraph Presentation ["5. BI Presentation Layer"]
        StreamlitUI["Enterprise Streamlit Dashboard<br/>(Responsive UI, Plotly Charts, Filters)"]
        PowerBIApp["Microsoft Power BI Desktop<br/>(Direct CSV / ODBC SQLite Connection)"]
        OLS --> StreamlitUI
        Forecast --> StreamlitUI
        WhatIf --> StreamlitUI
        PBIExport --> PowerBIApp
    end
```

## 2. Sequence Diagram (ETL Execution Flow)

```mermaid
sequenceDiagram
    autonumber
    actor User as Analyst / User
    participant App as Streamlit Dashboard
    participant ETL as ETL Pipeline Engine
    participant OS as Local File System (Desktop)
    participant DB as SQLite DB (orders)
    participant Models as Analytics & ML Engines

    User->>App: Launch Application / Request Rerun
    App->>ETL: Trigger run_pipeline()
    ETL->>OS: Locate and read Superstore CSV/Excel
    OS-->>ETL: Return raw records (9,994 rows)
    ETL->>ETL: Clean whitespace, validate ranges, compute derived metrics
    ETL->>DB: Recreate indexed schema & bulk insert
    ETL->>OS: Export cleaned_superstore.csv for Power BI
    DB-->>App: Fetch optimized aggregated slices
    App->>Models: Request Trend Line, Holt-Winters, & What-If models
    Models-->>App: Return regression metrics & forecast series
    App-->>User: Render interactive BI dashboard & KPIs
```

## 3. Database Schema (`superstore_bi.db`)

### Table: `orders`
| Column | Type | Description |
|---|---|---|
| `row_id` | INTEGER PRIMARY KEY | Unique surrogate identifier |
| `order_id` | TEXT | Unique transaction code (e.g., CA-2016-152156) |
| `order_date` | TEXT (ISO 8601) | Date of purchase (YYYY-MM-DD) |
| `ship_date` | TEXT (ISO 8601) | Date of fulfillment (YYYY-MM-DD) |
| `ship_mode` | TEXT | Fulfillment tier (Standard, Second Class, etc.) |
| `customer_id` | TEXT | Unique customer reference |
| `customer_name` | TEXT | Customer display name |
| `segment` | TEXT | Consumer / Corporate / Home Office |
| `country` | TEXT | Country jurisdiction (United States) |
| `city` | TEXT | City name |
| `state` | TEXT | State / Province |
| `postal_code` | TEXT | Formatted 5-digit postal code |
| `region` | TEXT | Geographic region (West, East, Central, South) |
| `product_id` | TEXT | Unique product inventory SKU |
| `category` | TEXT | Top-level merchandise division |
| `sub_category` | TEXT | Granular merchandise segment (17 classes) |
| `product_name` | TEXT | Full item description |
| `sales` | REAL | Total transaction sales value |
| `quantity` | INTEGER | Units purchased |
| `discount` | REAL | Commercial discount rate [0.0 - 0.8] |
| `profit` | REAL | Net transactional profit (positive or negative) |
| `shipping_days` | INTEGER | Elapsed days between order and dispatch |
| `order_year` | INTEGER | Calendar year extracted from order date |
| `order_month` | INTEGER | Calendar month number (1 - 12) |
| `order_month_name` | TEXT | Abbreviated month name (Jan - Dec) |
| `order_quarter` | TEXT | Fiscal quarter (Q1 - Q4) |
| `year_month` | TEXT | Year-month temporal index (YYYY-MM) |
| `profit_margin_pct`| REAL | Calculated as (Profit / Sales) * 100 |
| `unit_price` | REAL | Calculated as Sales / Quantity |
| `is_profitable` | INTEGER | Boolean flag: 1 if Profit > 0 else 0 |

### Indexes Built:
- `idx_orders_order_date` on `order_date`
- `idx_orders_region` on `region`
- `idx_orders_category` on `category`
- `idx_orders_sub_category` on `sub_category`
- `idx_orders_year_month` on `year_month`
- `idx_orders_customer` on `customer_id`
- `idx_orders_product` on `product_id`
