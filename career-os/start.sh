#!/bin/bash
cd "$(dirname "$0")"

if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing dependencies, one-time only..."
    pip3 install -r requirements.txt
fi

echo "Starting Career OS..."
( sleep 1 && open http://127.0.0.1:5000 2>/dev/null || xdg-open http://127.0.0.1:5000 2>/dev/null ) &
python3 app.py
