#!/bin/sh
set -e

python -c "from database import Base, engine; import models; Base.metadata.create_all(bind=engine)"
python seed.py

exec uvicorn main:app --host 0.0.0.0 --port 8000
