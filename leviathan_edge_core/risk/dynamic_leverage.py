from config import Config

def dynamic_leverage(score: float, strategy: str, direction: str,
                     drawdown: float, era_active: bool) -> int:
    cap = Config.LEVERAGE_CAPS.get(strategy, 5)
    cap = int(cap * (Config.LONG_FACTOR if direction == "LONG" else Config.SHORT_FACTOR))
    if score >= 85:
        cap = min(cap + 1, 8)
    elif score < 70:
        cap = max(cap - 1, 2)
    if drawdown > 0.10:
        cap = max(cap - 2, 2)
    elif drawdown > 0.05:
        cap = max(cap - 1, 2)
    if era_active:
        cap = max(int(cap * Config.ERA_LEV_MULT), 2)
    return cap
