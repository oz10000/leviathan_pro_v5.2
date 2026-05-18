#!/bin/bash
cd "$(dirname "$0")/../streamlit_app"
while true; do
    if [ -f runtime/engine.pid ]; then
        pid=$(cat runtime/engine.pid)
        if ! kill -0 $pid 2>/dev/null; then
            echo "$(date) – Engine down, restarting..."
            python engine_runner.py &
            echo $! > runtime/engine.pid
        fi
    else
        echo "$(date) – PID file missing, starting engine..."
        python engine_runner.py &
        echo $! > runtime/engine.pid
    fi
    sleep 30
done
