from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class SessionLogger:
    """Singleton service that manages session-based CSV logging."""
    _instance: SessionLogger | None = None

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or Path("Logs")
        self.session_dir = self._create_session_dir()
        logger.info(f"Initialized SessionLogger in {self.session_dir}")

    @classmethod
    def get_instance(cls) -> SessionLogger:
        if cls._instance is None:
            # We assume current working directory is the project root (where Logs should be created)
            cls._instance = cls()
        return cls._instance

    def _create_session_dir(self) -> Path:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        highest_session = 0
        for item in self.root_dir.iterdir():
            if item.is_dir() and item.name.startswith("Session"):
                try:
                    num = int(item.name.replace("Session", ""))
                    if num > highest_session:
                        highest_session = num
                except ValueError:
                    pass
        
        new_session = highest_session + 1
        session_dir = self.root_dir / f"Session{new_session:02d}"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _append_to_csv(self, filename: str, headers: list[str], row: list[Any]) -> None:
        file_path = self.session_dir / filename
        file_exists = file_path.exists()
        
        try:
            with open(file_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(headers)
                writer.writerow(row)
        except Exception as e:
            logger.error(f"Failed to write to {file_path}: {e}")

    def log_system(self, action: str, level: str, message: str) -> None:
        """Backend startup/shutdown, errors, warnings"""
        timestamp = datetime.now(timezone.utc).isoformat()
        self._append_to_csv(
            "system_log.csv",
            ["Timestamp", "Action", "Level", "Message"],
            [timestamp, action, level, message]
        )

    def log_telemetry(self, uav_id: str, telemetry: Any) -> None:
        """Timestamp, UAV ID, RPM, EGT, CHT, oil pressure, etc."""
        # Using getattr safely, fallback to str representations or dict extraction
        t = telemetry
        ts = getattr(t, "timestamp", datetime.now(timezone.utc)).isoformat()
        
        row = [
            ts, uav_id, getattr(t, "rpm", ""), getattr(t, "throttle", ""), 
            getattr(t, "manifold_absolute_pressure", ""), getattr(t, "egt", ""), 
            getattr(t, "cht", ""), getattr(t, "intake_air_temperature", ""),
            getattr(t, "ambient_temperature", ""), getattr(t, "oil_pressure", ""),
            getattr(t, "oil_temperature", ""), getattr(t, "fuel_flow", ""),
            getattr(t, "vibration", ""), getattr(t, "ambient_pressure", ""),
            getattr(t, "battery_voltage", ""), getattr(t, "injection_timing_deg", "")
        ]
        
        self._append_to_csv(
            "telemetry_log.csv",
            [
                "Timestamp", "UAV_ID", "RPM", "Throttle", "MAP", "EGT", "CHT", 
                "Intake_Air_Temp", "Ambient_Temp", "Oil_Pressure", "Oil_Temp", 
                "Fuel_Flow", "Vibration", "Ambient_Pressure", "Battery_Voltage", 
                "Injection_Timing_Deg"
            ],
            row
        )

    def log_fault(self, uav_id: str, event_type: str, fault_type: str, severity: float, confidence: float) -> None:
        """Fault injected/detected, severity, confidence, timestamp"""
        timestamp = datetime.now(timezone.utc).isoformat()
        self._append_to_csv(
            "fault_log.csv",
            ["Timestamp", "UAV_ID", "Event_Type", "Fault_Type", "Severity", "Confidence"],
            [timestamp, uav_id, event_type, fault_type, severity, confidence]
        )

    def log_health(self, uav_id: str, state: Any) -> None:
        """Overall health + subsystem health over time"""
        timestamp = getattr(state, "timestamp", datetime.now(timezone.utc)).isoformat()
        row = [
            timestamp, uav_id, getattr(state, "overall_health", ""),
            getattr(state, "combustion_health", ""), getattr(state, "thermal_health", ""),
            getattr(state, "lubrication_health", ""), getattr(state, "mechanical_health", ""),
            getattr(state, "electrical_health", "")
        ]
        
        self._append_to_csv(
            "health_log.csv",
            [
                "Timestamp", "UAV_ID", "Overall_Health", "Combustion_Health",
                "Thermal_Health", "Lubrication_Health", "Mechanical_Health", "Electrical_Health"
            ],
            row
        )

    def log_analytics(self, uav_id: str, analytics: Any) -> None:
        """Anomaly score, degradation, RUL status/prediction"""
        timestamp = getattr(analytics, "timestamp", datetime.now(timezone.utc)).isoformat()
        
        anomaly_score = ""
        is_anomaly = ""
        if hasattr(analytics, "anomaly") and analytics.anomaly:
            anomaly_score = analytics.anomaly.score
            is_anomaly = analytics.anomaly.is_anomaly
            
        deg_index = ""
        deg_trend = ""
        if hasattr(analytics, "degradation") and analytics.degradation:
            deg_index = analytics.degradation.degradation_index
            deg_trend = analytics.degradation.trend
            
        rul_status = ""
        rul_time = ""
        if hasattr(analytics, "rul") and analytics.rul:
            rul_status = analytics.rul.status
            rul_time = analytics.rul.remaining_time_seconds
            
        self._append_to_csv(
            "analytics_log.csv",
            [
                "Timestamp", "UAV_ID", "Is_Anomaly", "Anomaly_Score", 
                "Degradation_Index", "Degradation_Trend", "RUL_Status", "RUL_Time_Seconds"
            ],
            [timestamp, uav_id, is_anomaly, anomaly_score, deg_index, deg_trend, rul_status, rul_time]
        )

    def log_mission(self, uav_id: str, event: str, details: str) -> None:
        """Mission start/end, events, anomalies, faults, recovery"""
        timestamp = datetime.now(timezone.utc).isoformat()
        self._append_to_csv(
            "mission_log.csv",
            ["Timestamp", "UAV_ID", "Event", "Details"],
            [timestamp, uav_id, event, details]
        )

    def log_api(self, method: str, path: str, status: int, latency_ms: float) -> None:
        """Endpoint requests/errors/latency"""
        timestamp = datetime.now(timezone.utc).isoformat()
        self._append_to_csv(
            "api_log.csv",
            ["Timestamp", "Method", "Path", "Status_Code", "Latency_ms"],
            [timestamp, method, path, status, f"{latency_ms:.2f}"]
        )

    def log_unity(self, uav_id: str, state: str, details: str) -> None:
        """Connection state, telemetry connection, WebSocket errors"""
        timestamp = datetime.now(timezone.utc).isoformat()
        self._append_to_csv(
            "unity_log.csv",
            ["Timestamp", "UAV_ID", "State", "Details"],
            [timestamp, uav_id, state, details]
        )

def get_session_logger() -> SessionLogger:
    return SessionLogger.get_instance()
