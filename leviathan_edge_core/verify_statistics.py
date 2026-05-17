import numpy as np
from analytics.expectancy_engine import ExpectancyEngine

def test_expectancy():
    engine = ExpectancyEngine()
    engine.add(10)
    engine.add(20)
    engine.add(-5)
    exp = engine.compute()
    assert exp > 0, "Expectancy should be positive"
    print("Expectancy OK:", exp)

if __name__ == "__main__":
    test_expectancy()
    print("Statistics checks passed.")
