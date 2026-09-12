import { useCallback, useEffect, useRef, useState } from "react";
import type {
  DashboardSnapshotResponse,
  HistoryPoint,
  MissionReportResponse,
  PerformanceMapResponse,
  UAVItem,
} from "../types/api";
import { api } from "../services/api";
import { type ConnectionStatus, TwinWebSocketClient } from "../services/websocket";

const MAX_HISTORY = 60;

export function useDigitalTwin(defaultUavId: string = "UAV-001") {
  const [uavId, setUavId] = useState<string>(defaultUavId);
  const [uavList, setUavList] = useState<UAVItem[]>([]);
  const [snapshot, setSnapshot] = useState<DashboardSnapshotResponse | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [missionReport, setMissionReport] = useState<MissionReportResponse | null>(null);
  const [performanceMap, setPerformanceMap] = useState<PerformanceMapResponse | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("CONNECTING");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const wsClientRef = useRef<TwinWebSocketClient | null>(null);

  // 1. Fetch or initialize UAVs
  const loadUAVs = useCallback(async () => {
    try {
      const res = await api.listUAVs();
      if (res.uavs.length === 0) {
        // Pre-register UAV-001 if no UAV exists
        try {
          const created = await api.registerUAV({
            uav_id: "UAV-001",
            engine_id: "ENG-UAV-001",
            model_type: "piston",
            metadata: { mission: "PATROL-RECON-ALPHA", operator: "AeroTwin Ground Base" },
          });
          setUavList([created]);
        } catch {
          // ignore if already registered
        }
      } else {
        setUavList(res.uavs);
      }
    } catch (err: any) {
      console.warn("Failed to list UAVs:", err);
    }
  }, []);

  // 2. Load initial REST snapshot, history, mission report, and performance map
  const loadInitialData = useCallback(async (targetUav: string) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch initial dashboard snapshot
      const snap = await api.getDashboard(targetUav);
      setSnapshot(snap);

      // Fetch recent history
      try {
        const histRes = await api.getHistory(targetUav, MAX_HISTORY);
        setHistory(histRes.points);
      } catch {
        // fallback to creating first point from snapshot
        if (snap) {
          setHistory([
            {
              timestamp: snap.timestamp,
              measurements: snap.engine,
              performance: snap.performance,
              health: snap.health,
              overall_health: snap.health.overall,
              is_anomaly: snap.analytics.anomaly.is_anomaly,
              anomaly_score: snap.analytics.anomaly.score,
              active_fault: snap.analytics.faults[0]?.fault_type || null,
              degradation_index: snap.analytics.degradation.degradation_index,
              rul_estimate: snap.analytics.rul.remaining_useful_life,
            },
          ]);
        }
      }

      // Fetch mission report & performance map
      try {
        const rep = await api.getMissionReport(targetUav);
        setMissionReport(rep);
      } catch (err) {
        console.warn("Could not load mission report:", err);
      }

      try {
        const pmap = await api.getPerformanceMap(targetUav);
        setPerformanceMap(pmap);
      } catch (err) {
        console.warn("Could not load performance map:", err);
      }
    } catch (err: any) {
      console.error("Initial load failed for UAV:", targetUav, err);
      setError(err.message || "Failed to load Digital Twin snapshot");
    } finally {
      setLoading(false);
    }
  }, []);

  // 3. Handle live incoming snapshot from WebSocket
  const handleLiveSnapshot = useCallback((newSnap: DashboardSnapshotResponse) => {
    setSnapshot(newSnap);

    // Append to bounded rolling history
    setHistory((prev) => {
      const newPoint: HistoryPoint = {
        timestamp: newSnap.timestamp,
        measurements: newSnap.engine,
        performance: newSnap.performance,
        health: newSnap.health,
        overall_health: newSnap.health.overall,
        is_anomaly: newSnap.analytics.anomaly.is_anomaly,
        anomaly_score: newSnap.analytics.anomaly.score,
        active_fault: newSnap.analytics.faults[0]?.fault_type || null,
        degradation_index: newSnap.analytics.degradation.degradation_index,
        rul_estimate: newSnap.analytics.rul.remaining_useful_life,
      };

      const updated = [...prev, newPoint];
      if (updated.length > MAX_HISTORY) {
        return updated.slice(updated.length - MAX_HISTORY);
      }
      return updated;
    });

    // Update performance map current point live
    setPerformanceMap((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        current_point: {
          rpm: newSnap.engine.rpm,
          throttle: newSnap.engine.throttle,
          engine_load: newSnap.performance.engine_load,
          torque_nm: newSnap.performance.estimated_torque,
          power_kw: newSnap.performance.estimated_power / 1000.0,
          fuel_flow: newSnap.engine.fuel_flow,
          fuel_efficiency: newSnap.performance.fuel_efficiency,
        },
      };
    });
  }, []);

  // 4. Initialize WebSocket on UAV change
  useEffect(() => {
    loadUAVs();
    loadInitialData(uavId);

    const client = new TwinWebSocketClient(
      (newSnap) => handleLiveSnapshot(newSnap),
      (newStatus) => setStatus(newStatus)
    );
    wsClientRef.current = client;
    client.connect(uavId);

    return () => {
      client.disconnect();
    };
  }, [uavId, loadUAVs, loadInitialData, handleLiveSnapshot]);

  // Refresh mission report periodically or on demand
  const refreshMissionReport = useCallback(async () => {
    try {
      const rep = await api.getMissionReport(uavId);
      setMissionReport(rep);
    } catch (err) {
      console.warn("Failed to refresh mission report:", err);
    }
  }, [uavId]);

  const refreshPerformanceMap = useCallback(async () => {
    try {
      const pmap = await api.getPerformanceMap(uavId);
      setPerformanceMap(pmap);
    } catch (err) {
      console.warn("Failed to refresh performance map:", err);
    }
  }, [uavId]);

  return {
    uavId,
    setUavId,
    uavList,
    snapshot,
    history,
    missionReport,
    performanceMap,
    status,
    loading,
    error,
    refreshMissionReport,
    refreshPerformanceMap,
  };
}
