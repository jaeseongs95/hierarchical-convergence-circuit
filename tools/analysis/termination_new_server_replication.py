"""r15 new-host replication; keep the pinned r14 numerical/lifecycle engine."""
from pathlib import Path
import termination_server_crossover as server

server.SELF = Path(__file__).resolve()
server.PUB = server.ROOT / 'evidence/new-server-replication-20261018-r15'

if __name__ == '__main__':
    server.main()
