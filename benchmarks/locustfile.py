"""
SeriCare / Setu - IoT & Mobile Scalability Benchmark Suite
Simulates realistic workloads:
1. IoT Sensor Telemetry Stream (High Frequency Ingestion)
2. Mobile App Active Farmer Polling (Dashboard + Telemetry SSE/Polling)
3. Actuator Control & Command Lifecycle (Transactional writes)
"""

import time
import random
import uuid
from locust import HttpUser, task, between, events

class TelemetryDeviceUser(HttpUser):
    """Simulates an IoT sensor gateway pushing environmental telemetry."""
    wait_time = between(1.0, 3.0)

    def on_start(self):
        self.device_id = f"device_bench_{random.randint(1, 500):03d}"
        self.shed_id = f"shed_{random.randint(1, 100):02d}"
        self.headers = {
            "X-Device-Key": "setu-iot-device-key-2026",
            "Content-Type": "application/json"
        }
        self.seq = 0

    @task(10)
    def post_telemetry_single(self):
        self.seq += 1
        payload = {
            "shed_id": self.shed_id,
            "device_id": self.device_id,
            "event_id": str(uuid.uuid4()),
            "sequence_number": self.seq,
            "indoor_temp": round(random.uniform(24.0, 32.0), 2),
            "indoor_humidity": round(random.uniform(60.0, 90.0), 2),
            "indoor_air_quality": round(random.uniform(70.0, 99.0), 1),
            "indoor_light_lux": round(random.uniform(10.0, 50.0), 1)
        }
        self.client.post(
            "/api/v1/telemetry/record",
            json=payload,
            headers=self.headers,
            name="/api/v1/telemetry/record"
        )

    @task(3)
    def post_telemetry_batch(self):
        events = []
        for _ in range(5):
            self.seq += 1
            events.append({
                "shed_id": self.shed_id,
                "device_id": self.device_id,
                "event_id": str(uuid.uuid4()),
                "sequence_number": self.seq,
                "indoor_temp": round(random.uniform(25.0, 30.0), 2),
                "indoor_humidity": round(random.uniform(70.0, 85.0), 2),
                "indoor_air_quality": round(random.uniform(80.0, 95.0), 1),
                "indoor_light_lux": round(random.uniform(15.0, 35.0), 1)
            })
        self.client.post(
            "/api/v1/telemetry/batch",
            json={"readings": events},
            headers=self.headers,
            name="/api/v1/telemetry/batch"
        )


class FarmerMobileUser(HttpUser):
    """Simulates active mobile app user monitoring rearing sheds."""
    wait_time = between(2.0, 5.0)

    def on_start(self):
        self.shed_id = "shed_01"
        self.auth_token = None
        # Authenticate as ramesh_farmer or admin
        login_res = self.client.post(
            "/api/v1/auth/login",
            json={"username": "ramesh_farmer", "password": "setu2026"}
        )
        if login_res.status_code == 200:
            self.auth_token = login_res.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}" if self.auth_token else "",
            "Content-Type": "application/json"
        }

    @task(12)
    def get_shed_overview(self):
        self.client.get(
            f"/api/v1/sheds/{self.shed_id}",
            headers=self.headers,
            name="/api/v1/sheds/[shed_id]"
        )

    @task(4)
    def get_weather(self):
        self.client.get(
            "/api/v1/weather/live",
            headers=self.headers,
            name="/api/v1/weather/live"
        )

    @task(3)
    def get_ai_explanation(self):
        self.client.get(
            f"/api/v1/ai/explain/{self.shed_id}?lang=en",
            headers=self.headers,
            name="/api/v1/ai/explain/[shed_id]"
        )

    @task(1)
    def toggle_actuator_override(self):
        self.client.post(
            f"/api/v1/control/{self.shed_id}/override",
            json={
                "cooler": random.choice([True, False]),
                "fan": random.choice([True, False]),
                "heater": False,
                "light": False,
                "light_brightness": 50
            },
            headers=self.headers,
            name="/api/v1/control/[shed_id]/override"
        )


class EdgeCommandWorkerUser(HttpUser):
    """Simulates IoT Edge controller polling for pending control commands and ACKing."""
    wait_time = between(1.5, 4.0)

    def on_start(self):
        self.device_id = f"device_bench_{random.randint(1, 100):03d}"
        self.headers = {
            "X-Device-Key": "setu-iot-device-key-2026",
            "Content-Type": "application/json"
        }

    @task(5)
    def poll_and_ack_commands(self):
        res = self.client.get(
            f"/api/v1/control/commands/{self.device_id}/pending",
            headers=self.headers,
            name="/api/v1/control/commands/[device_id]/pending"
        )
        if res.status_code == 200:
            data = res.json()
            commands = data.get("commands", [])
            for cmd in commands:
                cmd_id = cmd.get("command_id")
                if cmd_id:
                    self.client.post(
                        "/api/v1/control/commands/ack",
                        json={
                            "command_id": cmd_id,
                            "device_id": self.device_id,
                            "status": "APPLIED",
                            "execution_details": {"firmware": "v2.4.1", "duration_ms": 12}
                        },
                        headers=self.headers,
                        name="/api/v1/control/commands/ack"
                    )
