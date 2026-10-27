@echo off
echo ========================================================
echo  Starting Havells Billing MIS Intelligence Dashboard
echo ========================================================

IF NOT EXIST venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate.bat
)

echo Running migrations...
python manage.py migrate

echo Bootstrapping administrator and sample data...
python manage.py setup_havells_data

echo Launching server at http://127.0.0.1:8000/
python manage.py runserver 127.0.0.1:8000
pause
