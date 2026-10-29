#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Running database migrations..."
python manage.py migrate

echo "==> Initializing RBAC Roles and Permissions..."
python manage.py init_rbac

echo "==> Build completed successfully!"
