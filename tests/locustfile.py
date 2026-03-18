"""Load tests for Satoshi API — Sprint 3 scenarios.

Scenarios:
  Baseline:   locust -f tests/locustfile.py --host http://localhost:9332 -u 50 -r 10 -t 5m
  Scale:      locust -f tests/locustfile.py --host http://localhost:9332 -u 500 -r 50 -t 10m
  Spike:      locust -f tests/locustfile.py SpikeUser --host http://localhost:9332 -u 200 -r 200 -t 5m
  Endurance:  locust -f tests/locustfile.py --host http://localhost:9332 -u 50 -r 5 -t 60m

Azure Load Testing: Upload this file to Azure Load Testing service.
"""
from locust import HttpUser, LoadTestShape, task, between, constant_pacing


class BitcoinAPIUser(HttpUser):
    """Standard user — weighted mix of all endpoints."""
    wait_time = between(0.5, 2)

    @task(5)
    def health(self):
        self.client.get("/api/v1/health")

    @task(3)
    def fees_recommended(self):
        self.client.get("/api/v1/fees/recommended")

    @task(3)
    def mempool(self):
        self.client.get("/api/v1/mempool")

    @task(2)
    def latest_block(self):
        self.client.get("/api/v1/blocks/latest")

    @task(2)
    def network(self):
        self.client.get("/api/v1/network")

    @task(2)
    def mining(self):
        self.client.get("/api/v1/mining")

    @task(1)
    def fee_target(self):
        self.client.get("/api/v1/fees/6")

    @task(1)
    def mempool_info(self):
        self.client.get("/api/v1/mempool/info")

    @task(2)
    def fee_landscape(self):
        self.client.get("/api/v1/fees/landscape")

    @task(1)
    def fee_plan(self):
        self.client.get("/api/v1/fees/plan?profile=simple_send")

    @task(1)
    def prices(self):
        self.client.get("/api/v1/prices")

    @task(1)
    def supply(self):
        self.client.get("/api/v1/supply")


class SpikeUser(HttpUser):
    """Spike scenario — all users arrive instantly, hammer fee endpoints."""
    wait_time = constant_pacing(0.5)  # 2 req/sec per user

    @task(5)
    def fees_recommended(self):
        self.client.get("/api/v1/fees/recommended")

    @task(3)
    def fees_landscape(self):
        self.client.get("/api/v1/fees/landscape")

    @task(2)
    def health(self):
        self.client.get("/api/v1/health")


class RampShape(LoadTestShape):
    """Custom shape for Scale scenario — ramp from 0 to 500 over 10 min.

    Usage: locust -f tests/locustfile.py --host <url>
           (LoadTestShape auto-controls user count, ignore -u/-r flags)
    Enable by setting LOCUST_SHAPE=ramp environment variable.
    """
    stages = [
        {"duration": 60, "users": 50, "spawn_rate": 10},     # Warm up
        {"duration": 180, "users": 200, "spawn_rate": 25},    # Ramp
        {"duration": 360, "users": 500, "spawn_rate": 50},    # Peak
        {"duration": 480, "users": 500, "spawn_rate": 50},    # Sustain
        {"duration": 600, "users": 0, "spawn_rate": 100},     # Cool down
    ]

    def tick(self):
        import os
        if os.environ.get("LOCUST_SHAPE") != "ramp":
            return None  # Disabled — use manual -u/-r

        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None
