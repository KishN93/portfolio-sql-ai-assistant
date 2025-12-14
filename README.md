# 📊 Portfolio SQL and AI Assistant

A portfolio analytics assistant that combines deterministic SQL based calculations with a guarded AI explanation layer.  
The system answers natural language questions about portfolio holdings, NAV, performance, and drivers while ensuring all numbers come from verified data sources.

---

## 🔍 What problem does this solve

Investment teams spend time manually reconciling portfolio data across spreadsheets and systems to answer questions such as:

• What was the portfolio NAV on a given day  
• What drove a large move in performance  
• Which holdings contributed most to PnL  
• How did cash movements affect returns  

This project demonstrates how those questions can be answered using a transparent SQL engine, with AI used only to explain results rather than calculate them.

---

## 🧠 Key design principle

**AI never calculates numbers**

All financial calculations are:
• Deterministic  
• SQL driven  
• Reproducible  
• Verifiable in Excel  

The AI layer only consumes validated outputs and converts them into human readable commentary.

---

## 🏗️ Architecture overview

📁 Excel portfolio data  
⬇  
🗄️ SQLite database  
⬇  
📐 SQL queries for NAV, PnL, returns, attribution  
⬇  
🛡️ Rule engine and guardrails  
⬇  
🤖 LLM explanation layer  
⬇  
💬 Natural language portfolio answers  

---

## 📂 Project structure

portfolio_sql_data_project/

├── portfolio_data_extended.xlsx   # Synthetic portfolio data  
├── load_excel_to_sqlite.py         # Loads Excel into SQLite  
├── db_queries.py                   # Core SQL queries  
├── rule_engine.py                  # Business logic and thresholds  
├── guardrails.py                   # Query validation and safety  
├── llm_explainer.py                # AI explanation layer  
├── qa_assistant.py                 # Interactive portfolio assistant  
├── run_sql.py                      # Example analytics queries  
└── .gitignore                      # Excludes database and secrets  

---

## 💬 Example questions you can ask

NAV on 2025-01-13  
Explain 2025-01-20  
Show big moves  
What is my holding in AAPL  

---

## ⚙️ How to run locally

Clone the repository:

git clone https://github.com/KishN93/portfolio-sql-ai-assistant.git  
cd portfolio-sql-ai-assistant  

Create environment and install dependencies:

conda create -n portfolio_env python=3.10  
conda activate portfolio_env  
pip install -r requirements.txt  

Set OpenAI API key:

setx OPENAI_API_KEY "your_api_key_here"  

Load data into SQLite:

python load_excel_to_sqlite.py  

Start the assistant:

python qa_assistant.py  

---

## 🔐 Security and data handling

• API keys are stored as environment variables  
• Database files are excluded from version control  
• Portfolio data is synthetic and included for reproducibility  
• AI does not have write access to data or calculations  

This mirrors best practice used in financial institutions.

---

## 🚀 Why this project matters

This project demonstrates:
• SQL proficiency applied to finance  
• Portfolio analytics and NAV logic  
• Responsible and explainable AI usage  
• Strong separation of concerns  
• Production minded data handling  

It is designed as a realistic foundation for portfolio analytics, operations, or data science roles within asset management or fintech.

---

## 📌 Future extensions

• Support for multiple portfolios  
• Time weighted and money weighted returns  
• Factor attribution  
• Interactive dashboard  
• Automated anomaly detection  

---

## 👤 Author

Built by Kishan  
MSc Data Science and AI  
Background in Investment Operations
