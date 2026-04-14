#!/bin/bash
set -e
exec python3 -m celery -A celery_app worker --loglevel=info -Q documents
