import logging
from runtime.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def main():
    orch = Orchestrator()
    orch.run()

if __name__ == "__main__":
    main()
