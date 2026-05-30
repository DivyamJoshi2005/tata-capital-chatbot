@echo off
echo Setting up Tata Capital Chatbot Environment...

echo Creating virtual environment...
python -m venv .venv

echo Activating virtual environment...
call .venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Environment setup complete!
echo To run the web server, use: uvicorn api:app --host 0.0.0.0 --port 8000
pause
