"""Load test for Satoshi API.

Run with: locust -f tests/locustfile.py --host http://localhost:9332
Target: 50 concurrent users, 60 seconds, p95 < 500ms
"""
from locust import HttpUser, task, between


class BitcoinAPIUser(HttpUser):
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
