#!/bin/bash
cd "$(dirname "$0")/../streamlit_app"
nohup python engine_runner.py > ../logs/engine.log 2>&1 &
echo $! > runtime/engine.pid
echo "Engine started with PID $(cat runtime/engine.pid)"
