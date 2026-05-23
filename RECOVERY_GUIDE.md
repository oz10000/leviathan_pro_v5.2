# Recovery Guide
If the system stops unexpectedly:
1. Check `runtime/state.json` and `runtime/logs/engine.log`.
2. If circuit breaker is active, wait for cooldown.
3. To resume, ensure `runtime_control.json` has `bot_enabled: true`.
4. Restart the GitHub Actions workflow or run `python runtime/orchestrator.py` manually.
