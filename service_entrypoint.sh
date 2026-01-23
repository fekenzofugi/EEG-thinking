#!/bin/bash

sleep 1

cd code

flask db migrate

flask db upgrade

gunicorn --workers 4 --threads 8 --bind 0.0.0.0:5000 app.run:app