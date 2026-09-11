import type {
  DashboardSnapshotResponse,
  HistoryResponse,
  MissionReportResponse,
  PerformanceMapResponse,
  SimulationStatusResponse,
  UAVItem,
} from "../types/api";

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      // ignore
    }
    throw new Error(`API Error [${res.status}]: ${errorDetail}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  getHealth: () => request<{ status: string; version: string; service: string }>("/health"),

  listUAVs: () => request<{ total: number; uavs: UAVItem[] }>("/api/v1/uavs"),

  registerUAV: (payload: { uav_id: string; engine_id?: string; model_type?: string; metadata?: any }) =>
    request<UAVItem>("/api/v1/uavs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getDashboard: (uavId: string) =>
    request<DashboardSnapshotResponse>(`/api/v1/uavs/${encodeURIComponent(uavId)}/dashboard`),

  getHistory: (uavId: string, limit = 60) =>
    request<HistoryResponse>(`/api/v1/uavs/${encodeURIComponent(uavId)}/history?limit=${limit}`),

  getMissionReport: (uavId: string) =>
    request<MissionReportResponse>(`/api/v1/uavs/${encodeURIComponent(uavId)}/mission-report`),

  getPerformanceMap: (uavId: string) =>
    request<PerformanceMapResponse>(`/api/v1/uavs/${encodeURIComponent(uavId)}/performance-map`),

  startSimulation: (uavId: string, throttle = 45.0) =>
    request<SimulationStatusResponse>(`/api/v1/uavs/${encodeURIComponent(uavId)}/simulation/start`, {
      method: "POST",
      body: JSON.stringify({ throttle, ambient_temperature: 24.0, ambient_pressure: 101.3 }),
    }),

  stepSimulation: (uavId: string, dt = 0.5) =>
    request<{ step_dt: number; dashboard_snapshot: DashboardSnapshotResponse }>(
      `/api/v1/uavs/${encodeURIComponent(uavId)}/simulation/step`,
      {
        method: "POST",
        body: JSON.stringify({ dt, auto_ingest: true }),
      }
    ),

  setThrottle: (uavId: string, throttle: number) =>
    request<SimulationStatusResponse>(`/api/v1/uavs/${encodeURIComponent(uavId)}/simulation/throttle`, {
      method: "POST",
      body: JSON.stringify({ throttle }),
    }),

  injectFault: (uavId: string, faultType: string | null) =>
    request<SimulationStatusResponse>(`/api/v1/uavs/${encodeURIComponent(uavId)}/simulation/fault`, {
      method: "POST",
      body: JSON.stringify({ fault_type: faultType }),
    }),

  resetSimulation: (uavId: string) =>
    request<SimulationStatusResponse>(`/api/v1/uavs/${encodeURIComponent(uavId)}/simulation/reset`, {
      method: "POST",
    }),
};
