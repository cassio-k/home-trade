@echo off
echo [1/2] Iniciando o Backend (FastAPI)...
start /b cmd /k "venv\Scripts\activate && uvicorn api.main:app"

echo [2/2] Iniciando o Frontend (Streamlit)...
start cmd /k "venv\Scripts\activate && streamlit run interface/Home.py"

echo Sistema inicializado com sucesso!