"""
SeriCare / Setu - High-Performance Asynchronous Load Test Runner
Empirical load testing utility measuring:
- Requests Per Second (Throughput)
- Latency percentiles: p50, p95, p99, min, max
- Concurrent worker connections
- Error rates and HTTP status breakdowns
"""

import sys
import os
import time
import asyncio
import statistics
import random
import uuid
from typing import List, Dict, Any

# Ensure backend path is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import httpx
from app.main import app

class BenchmarkResult:
    def __init__(self, name: str, concurrency: int, duration_sec: float):
        self.name = name
        self.concurrency = concurrency
        self.duration_sec = duration_sec
        self.latencies_ms: List[float] = []
        self.status_codes: Dict[int, int] = {}
        self.errors = 0
        self.total_requests = 0

    def record(self, status: int, latency_ms: float):
        self.total_requests += 1
        self.latencies_ms.append(latency_ms)
        self.status_codes[status] = self.status_codes.get(status, 0) + 1
        if status >= 400:
            self.errors += 1

    def print_summary(self):
        if not self.latencies_ms:
            print(f"[{self.name}] No requests recorded.")
            return

        sorted_lat = sorted(self.latencies_ms)
        n = len(sorted_lat)
        p50 = sorted_lat[int(n * 0.50)]
        p90 = sorted_lat[int(n * 0.90)]
        p95 = sorted_lat[int(n * 0.95)]
        p99 = sorted_lat[int(n * 0.99)]
        avg = statistics.mean(sorted_lat)
        rps = self.total_requests / self.duration_sec if self.duration_sec > 0 else 0

        print(f"\n{'='*70}")
        print(f" BENCHMARK REPORT: {self.name}")
        print(f"{'='*70}")
        print(f" Concurrency Level : {self.concurrency} concurrent workers")
        print(f" Duration           : {self.duration_sec:.2f} seconds")
        print(f" Total Requests     : {self.total_requests:,}")
        print(f" Throughput (RPS)   : {rps:,.2f} req/sec")
        print(f" Error Rate         : {(self.errors / self.total_requests * 100):.2f}% ({self.errors} errors)")
        print(f" Latency Min        : {min(sorted_lat):.2f} ms")
        print(f" Latency p50 (Med)  : {p50:.2f} ms")
        print(f" Latency p90        : {p90:.2f} ms")
        print(f" Latency p95        : {p95:.2f} ms")
        print(f" Latency p99        : {p99:.2f} ms")
        print(f" Latency Max        : {max(sorted_lat):.2f} ms")
        print(f" Latency Mean       : {avg:.2f} ms")
        print(f" Status Codes       : {dict(self.status_codes)}")
        print(f"{'='*70}\n")


async def run_telemetry_ingestion_bench(client: httpx.AsyncClient, concurrency: int = 50, duration: int = 5):
    """Measures raw telemetry ingestion write throughput and latency."""
    res = BenchmarkResult(f"Telemetry Ingestion API ({concurrency} workers)", concurrency, duration)
    headers = {
        "X-Device-Key": "setu-iot-device-key-2026",
        "Content-Type": "application/json"
    }

    stop_event = asyncio.Event()

    async def worker(worker_id: int):
        seq = 0
        device_id = f"bench_node_{worker_id:03d}"
        while not stop_event.is_set():
            seq += 1
            payload = {
                "shed_id": f"shed_{random.randint(1, 10):02d}",
                "device_id": device_id,
                "event_id": str(uuid.uuid4()),
                "sequence_number": seq,
                "temperature": round(random.uniform(25.0, 31.0), 2),
                "humidity": round(random.uniform(65.0, 85.0), 2),
                "air_quality": round(random.uniform(80.0, 95.0), 1),
                "light_lux": round(random.uniform(15.0, 40.0), 1)
            }
            t0 = time.perf_counter()
            try:
                r = await client.post("/api/v1/telemetry/record", json=payload, headers=headers)
                t1 = time.perf_counter()
                res.record(r.status_code, (t1 - t0) * 1000.0)
            except Exception as e:
                t1 = time.perf_counter()
                res.record(500, (t1 - t0) * 1000.0)

    start_time = time.perf_counter()
    tasks = [asyncio.create_task(worker(i)) for i in range(concurrency)]
    await asyncio.sleep(duration)
    stop_event.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    res.duration_sec = time.perf_counter() - start_time
    return res


async def run_mobile_dashboard_bench(client: httpx.AsyncClient, concurrency: int = 50, duration: int = 5):
    """Measures mobile client read throughput on getShedOverview."""
    # Obtain auth token
    login_res = await client.post("/api/v1/auth/login", json={"username": "ramesh_farmer", "password": "setu2026"})
    token = login_res.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    res = BenchmarkResult(f"Mobile Dashboard Reads ({concurrency} workers)", concurrency, duration)
    stop_event = asyncio.Event()

    async def worker(worker_id: int):
        shed_id = "shed_01"
        while not stop_event.is_set():
            t0 = time.perf_counter()
            try:
                r = await client.get(f"/api/v1/sheds/{shed_id}", headers=headers)
                t1 = time.perf_counter()
                res.record(r.status_code, (t1 - t0) * 1000.0)
            except Exception as e:
                t1 = time.perf_counter()
                res.record(500, (t1 - t0) * 1000.0)

    start_time = time.perf_counter()
    tasks = [asyncio.create_task(worker(i)) for i in range(concurrency)]
    await asyncio.sleep(duration)
    stop_event.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    res.duration_sec = time.perf_counter() - start_time
    return res


async def main():
    print("Initializing SeriCare Local Load Testing Benchmark...")
    transport = httpx.ASGITransport(app=app)
    limits = httpx.Limits(max_keepalive_connections=500, max_connections=1000)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", limits=limits, timeout=10.0) as client:
        # Warm up & cache priming
        print("Executing warm-up requests & cache priming...")
        for _ in range(5):
            await client.get("/health")

        login_res = await client.post("/api/v1/auth/login", json={"username": "ramesh_farmer", "password": "setu2026"})
        token = login_res.json().get("access_token", "")
        warm_headers = {"Authorization": f"Bearer {token}"}
        await client.get("/api/v1/sheds/shed_01", headers=warm_headers)
        print("Warm-up complete.")

        # Ingestion Benchmark at 20 concurrency
        b1 = await run_telemetry_ingestion_bench(client, concurrency=20, duration=5)
        b1.print_summary()

        # Ingestion Benchmark at 100 concurrency
        b2 = await run_telemetry_ingestion_bench(client, concurrency=100, duration=6)
        b2.print_summary()

        # Mobile Reads Benchmark at 50 concurrency
        b3 = await run_mobile_dashboard_bench(client, concurrency=50, duration=5)
        b3.print_summary()

        # Mobile Reads Benchmark at 200 concurrency
        b4 = await run_mobile_dashboard_bench(client, concurrency=200, duration=6)
        b4.print_summary()

if __name__ == "__main__":
    asyncio.run(main())
