@echo off

REM === Activate Anaconda ===
call "E:\Anaconda\Scripts\activate.bat"

REM === Activate project environment ===
call conda activate fraud_detection_env

REM === Navigate to project directory ===
cd /d "E:\Data Science Projects\portfolio_sql_data_project"

REM === Run Streamlit via Python module ===
python -m streamlit run App.py

pause
