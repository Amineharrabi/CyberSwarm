# Red's tool runtime. Lives only on attacker_net, no internet egress. Holds a small set
# of standard recon/testing utilities scoped to the lab. NO denial-of-service tooling.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        nmap \
        curl \
        iproute2 \
        iputils-ping \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir requests

# Red calls these via `docker exec` from the orchestrator's typed tool wrappers, which
# the guard validates (lab subnets only, call/time budgets) before anything runs.
CMD ["sleep", "infinity"]
