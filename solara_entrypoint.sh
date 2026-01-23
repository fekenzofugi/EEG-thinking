#!/bin/bash

# Run the app
SOLARA_APP=download.py gunicorn --workers 2 --threads 4 -b 0.0.0.0:5001 app:app