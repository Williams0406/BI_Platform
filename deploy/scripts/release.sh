#!/usr/bin/env bash
set -euo pipefail

cd /opt/bi-platform/backend
source /opt/bi-platform/venv/bin/activate

python manage.py check --deploy --settings=config.settings.production
python manage.py migrate --noinput
python manage.py collectstatic --noinput

sudo systemctl restart bi-api
sudo systemctl restart bi-celery-fast
sudo systemctl restart bi-celery-python
sudo systemctl restart bi-celery-ml
sudo systemctl restart bi-celery-optimization
sudo systemctl restart bi-celery-maintenance
sudo systemctl restart bi-celery-beat

curl --fail --silent https://bi.example.com/api/v1/health/ready/
