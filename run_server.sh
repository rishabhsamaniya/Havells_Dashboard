#!/usr/bin/env bash
echo "========================================================"
echo " Starting Havells Billing MIS Intelligence Dashboard"
echo "========================================================"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

python manage.py migrate
python manage.py setup_havells_data
echo "Launching server at http://127.0.0.1:8000/"
python manage.py runserver 127.0.0.1:8000
