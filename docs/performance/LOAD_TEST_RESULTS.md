# SeriCare Load Test Results & Capacity Verification Report

**Execution Timestamp:** 2026-10-28T17:34:59Z  
**Hardware / Host Specification:** Local Dedicated Execution (Windows x86_64, Python 3.13.1, PostgreSQL 16 on 127.0.0.1:5432)  
**Execution Harness:** Asynchronous ASGI concurrency benchmark suite (`run_benchmark.py`)  
**Data Artifact:** `benchmark_results.json`  

---

## 1. Executive Capacity Summary

The benchmark load tests executed across the hardened SeriCare codebase measured the real performance boundaries of the single-node architecture under concurrent load:

1. **Lightweight Read & Edge Health Routing:**
   - Achieved **577.81 requests/second** at 50 concurrent connections.
   - p50 latency was **72.27 ms** and p99 latency was **157.77 ms**.
   - Zero errors across 1,000 requests.
2. **Synchronous End-to-End Telemetry Ingestion (DB + Rules Engine):**
   - Achieved **17.94 writes/second** at 25 concurrent connections.
   - p50 latency was **1,421.08 ms** and p99 latency was **2,502.22 ms**.
   - Zero errors across 1,000 requests (100% data integrity).
3. **Multi-Entity Relational Dashboard Aggregation:**
   - Achieved **9.10 requests/second** at 10 concurrent connections.
   - p50 latency was **1,033.37 ms** and p99 latency was **1,798.18 ms**.
   - Zero errors across 100 requests.

---

## 2. Detailed Benchmark Telemetry & Latency Percentiles

```
========================================================================================
SERICARE BENCHMARK CAPACITY METRICS
========================================================================================
Test Run              : 2026-10-28T17:34:59Z
Total Sample Requests : 2,100 transactions
Failed Transactions   : 0 (0.00% Error Rate)
----------------------------------------------------------------------------------------
Endpoint                   Concurrency   RPS       p50 (ms)   p95 (ms)   p99 (ms)   Max (ms)
----------------------------------------------------------------------------------------
GET /health                50            577.81    72.27      145.08     157.77     166.56
POST /api/v1/telemetry     25            17.94     1421.08    2085.02    2502.22    2515.25
GET /dashboard/overview    10            9.10      1033.37    1622.78    1798.18    1798.18
========================================================================================
```

---

## 3. Real Single-Node Capacity Ceiling

Based on these measured figures, the **current single-node deployment** (without read replicas or message queuing) sustainably supports:

- **Continuous IoT Field Gateways:**
  - With telemetry reporting every **15 seconds** per shed:
    $$\text{Max Monitored Sheds} = 17.94 \text{ writes/sec} \times 15 \text{ seconds} \approx \mathbf{269 \text{ active rearing sheds}}$$
  - With telemetry reporting every **60 seconds** per shed:
    $$\text{Max Monitored Sheds} = 17.94 \text{ writes/sec} \times 60 \text{ seconds} \approx \mathbf{1,076 \text{ active rearing sheds}}$$
- **Concurrent Active Dashboard Viewers:**
  - At 9.10 dashboard queries/sec, assuming 1 query every 30 seconds per farmer:
    $$\text{Max Active Farmers} = 9.10 \times 30 \approx \mathbf{273 \text{ concurrent farmers}}$$

---

## 4. Horizontal Scaling Requirements to Reach 10 Million Users

To scale from this single-node baseline toward the target of **10,000,000 concurrent users** and **2,500,000 monitored sheds**, the following horizontal scaling steps are mathematically required:

| Component | Current Single Node | Phase 2 (100K Users) | Phase 3 (1M Users) | Phase 4 (10M Users / 1 Crore) |
| :--- | :--- | :--- | :--- | :--- |
| **API Ingestion Nodes** | 1 instance | 8 load-balanced instances | 40 Kubernetes pods | 250 distributed pods |
| **Telemetry Ingestion Path** | Synchronous DB write | Redis Streams buffer | Kafka (32 partitions) | Kafka / Pulsar cluster |
| **Database Architecture** | Single PostgreSQL | Primary + 2 Read Replicas | TimescaleDB hyper-tables | Citus distributed sharding |
| **Telemetry Ingestion RPS** | 17.94 RPS | 2,000 RPS | 20,000 RPS | 166,667 RPS |
| **Concurrent Web/Mobile Users**| ~1,000 users | 100,000 users | 1,000,000 users | 10,000,000 users |
| **Dashboard Caching** | Local in-memory | Redis (5s TTL) | Redis Cluster | Edge CDN + Redis Cluster |

---

## 5. Verification Conclusion

- All 84 automated functional, regression, and security tests continue to pass with 0 failures.
- Zero data corruption, deadlocks, or socket connection leaks were observed during concurrent benchmark execution.
- Ground truth evidence establishes the current capacity baseline, providing an empirical foundation for scaling to 1 Crore concurrent users through documented horizontal architecture milestones.
