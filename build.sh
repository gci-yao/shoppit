#!/usr/bin/env bash
set -o errexit

# Crée les dossiers nécessaires (au cas où)
mkdir -p media/img
mkdir -p media/products

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput  # Même sans static files
python manage.py migrate