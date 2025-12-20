# 📊 AVI Portfolio Analytics Dashboard

## 🧭 Overview
The AVI Portfolio Analytics Dashboard is a lightweight internal analytics tool designed to support investment and operations teams with transparent, auditable portfolio insights.

The application focuses on deterministic portfolio analysis, strong data quality controls, and clear visualisation rather than automation or black box decision making. It demonstrates how a Data Analyst can build internal tools that support portfolio monitoring, NAV validation, holdings analysis, and cash oversight in an investment management environment.

---

## 🚀 Key Features
- 📈 Portfolio NAV calculation by date with full transparency  
- 🧮 Security level portfolio breakdown including quantities, prices, market values, and NAV contribution  
- 📊 NAV analysis across selectable date ranges with time series visualisation  
- 📅 Daily NAV change tables to support validation and investigation  
- 📦 Holdings analysis by security and date  
- 💰 Cash balance monitoring with time series view and daily movement analysis  
- 🛡️ Robust data quality checks to prevent invalid or extreme inputs  
- 🧾 Deterministic SQL based calculations suitable for audit and review  

---

## 🗂️ Data Model
The portfolio is represented using a simple relational structure:

- 🏷️ **Securities** – instrument master data including ticker, name, asset class, and currency  
- 💵 **Prices** – daily closing prices for each security  
- 📊 **Holdings** – daily position quantities by security  
- 💰 **Cash** – daily cash balances  

All analytics are derived directly from these tables to ensure traceability.

---

## 🔐 Data Quality & Guardrails
Data integrity is enforced at multiple layers:

- ✅ Input validation during Excel ingestion  
  - Prices must be positive  
  - Quantities must be positive  
  - Cash balances must be non negative  
- 🚫 Extreme price movements are detected and blocked at load time  
- 🧱 SQLite constraints enforce structural correctness  
- 👀 The dashboard surfaces anomalies visually rather than silently correcting data  

This approach prevents corrupted data from entering the system while still allowing realistic market movements to be analysed transparently.

---

## 🏗️ Application Architecture
- 📁 Excel used as a controlled input source  
- 🐍 Python ingestion script validates and loads data into SQLite  
- 🗃️ SQL queries perform all portfolio calculations  
- 🖥️ Streamlit provides a clean internal analytics interface  
- ❌ No business logic embedded in the UI layer  

This separation ensures the application remains maintainable, auditable, and suitable for internal use.

---

## ▶️ How to Run the Application

```bash
conda activate fraud_detection_env
cd "E:\Data Science Projects\portfolio_sql_data_project"
python load_excel_to_sqlite.py
streamlit run App.py
