#!/bin/sh
. venv/bin/activate
pip install gunicorn==23.0.0
gunicorn --bind 0.0.0.0:5000 --workers=3 'wsgi:app(update_models=True)'