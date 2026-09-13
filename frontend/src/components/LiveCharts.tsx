import React, { useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { LineChart } from "lucide-react";
import type { HistoryPoint } from "../types/api";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface LiveChartsProps {
  history: HistoryPoint[];
}

export const LiveCharts: React.FC<LiveChartsProps> = ({ history }) => {
  const [activeTab, setActiveTab] = useState<"HEALTH" | "THERMAL" | "PROPULSION" | "FLUIDS">("HEALTH");

  const timestamps = history.map((h, i) => {
    try {
      const d = new Date(h.timestamp);
      return d.toLocaleTimeString([], { hour12: false, minute: "2-digit", second: "2-digit" });
    } catch {
      return `${i}s`;
    }
  });

  const chartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false, // Smooth high-frequency streaming
    interaction: {
      mode: "index",
      intersect: false,
    },
    plugins: {
      legend: {
        labels: {
          color: "#94a3b8",
          font: { family: "'Inter', sans-serif", size: 11, weight: "bold" },
          boxWidth: 12,
        },
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        titleColor: "#f8fafc",
        bodyColor: "#e2e8f0",
        borderColor: "rgba(56, 189, 248, 0.3)",
        borderWidth: 1,
        titleFont: { family: "'JetBrains Mono', monospace", size: 11 },
        bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
      },
    },
    scales: {
      x: {
        grid: { color: "rgba(255, 255, 255, 0.05)" },
        ticks: { color: "#64748b", font: { family: "'JetBrains Mono', monospace", size: 9 }, maxTicksLimit: 8 },
      },
      y: {
        grid: { color: "rgba(255, 255, 255, 0.05)" },
        ticks: { color: "#94a3b8", font: { family: "'JetBrains Mono', monospace", size: 10 } },
      },
    },
  };

  // 1. Health & Efficiency Data
  const healthData = {
    labels: timestamps,
    datasets: [
      {
        label: "Overall Health (%)",
        data: history.map((h) => h.overall_health),
        borderColor: "#10b981",
        backgroundColor: "rgba(16, 185, 129, 0.12)",
        fill: true,
        tension: 0.25,
        borderWidth: 2,
        pointRadius: 0,
      },
      {
        label: "Thermal Health (%)",
        data: history.map((h) => h.health?.thermal ?? 100),
        borderColor: "#f59e0b",
        backgroundColor: "transparent",
        tension: 0.25,
        borderWidth: 1.5,
        pointRadius: 0,
      },
      {
        label: "Fuel Efficiency (%)",
        data: history.map((h) => h.performance?.fuel_efficiency ?? 0),
        borderColor: "#38bdf8",
        backgroundColor: "transparent",
        tension: 0.25,
        borderWidth: 1.5,
        pointRadius: 0,
      },
    ],
  };

  // 2. Thermal Data (EGT & CHT)
  const thermalData = {
    labels: timestamps,
    datasets: [
      {
        label: "EGT (°C)",
        data: history.map((h) => h.measurements.egt),
        borderColor: "#ef4444",
        backgroundColor: "rgba(239, 68, 68, 0.1)",
        fill: true,
        tension: 0.25,
        borderWidth: 2,
        pointRadius: 0,
      },
      {
        label: "CHT (°C)",
        data: history.map((h) => h.measurements.cht),
        borderColor: "#f97316",
        backgroundColor: "transparent",
        tension: 0.25,
        borderWidth: 2,
        pointRadius: 0,
      },
    ],
  };

  // 3. Propulsion Data (RPM & Throttle)
  const propulsionData = {
    labels: timestamps,
    datasets: [
      {
        label: "RPM",
        data: history.map((h) => h.measurements.rpm),
        borderColor: "#0ea5e9",
        backgroundColor: "rgba(14, 165, 233, 0.1)",
        fill: true,
        tension: 0.25,
        borderWidth: 2,
        pointRadius: 0,
        yAxisID: "y",
      },
      {
        label: "Throttle (%)",
        data: history.map((h) => h.measurements.throttle),
        borderColor: "#a855f7",
        backgroundColor: "transparent",
        tension: 0.25,
        borderWidth: 1.5,
        pointRadius: 0,
        yAxisID: "y1",
      },
    ],
  };

  const propulsionOptions = {
    ...chartOptions,
    scales: {
      ...chartOptions.scales,
      y: {
        type: "linear",
        position: "left",
        grid: { color: "rgba(255, 255, 255, 0.05)" },
        ticks: { color: "#0ea5e9" },
      },
      y1: {
        type: "linear",
        position: "right",
        min: 0,
        max: 100,
        grid: { drawOnChartArea: false },
        ticks: { color: "#a855f7" },
      },
    },
  };

  // 4. Fluids & Vibration
  const fluidsData = {
    labels: timestamps,
    datasets: [
      {
        label: "Oil Pressure (psi)",
        data: history.map((h) => h.measurements.oil_pressure),
        borderColor: "#06b6d4",
        backgroundColor: "transparent",
        tension: 0.25,
        borderWidth: 2,
        pointRadius: 0,
      },
      {
        label: "Fuel Flow (L/h)",
        data: history.map((h) => h.measurements.fuel_flow),
        borderColor: "#eab308",
        backgroundColor: "transparent",
        tension: 0.25,
        borderWidth: 2,
        pointRadius: 0,
      },
      {
        label: "Vibration (mm/s)",
        data: history.map((h) => h.measurements.vibration),
        borderColor: "#ec4899",
        backgroundColor: "transparent",
        tension: 0.25,
        borderWidth: 1.5,
        pointRadius: 0,
      },
    ],
  };

  return (
    <div className="gcs-card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      
      {/* Header & Tabs */}
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", gap: "0.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <LineChart size={18} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.85rem", fontWeight: 700, letterSpacing: "0.04em", color: "#f8fafc" }}>
            REAL-TIME PROPULSION TELEMETRY & EFFICIENCY TRENDS
          </span>
        </div>

        {/* Tab Buttons */}
        <div style={{ display: "flex", gap: "0.35rem", background: "rgba(15, 23, 42, 0.8)", padding: "0.2rem", borderRadius: "6px" }}>
          <button
            onClick={() => setActiveTab("HEALTH")}
            style={{
              background: activeTab === "HEALTH" ? "rgba(14, 165, 233, 0.3)" : "transparent",
              color: activeTab === "HEALTH" ? "#38bdf8" : "#94a3b8",
              border: "none",
              padding: "0.25rem 0.6rem",
              borderRadius: "4px",
              fontSize: "0.72rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Health & Efficiency
          </button>

          <button
            onClick={() => setActiveTab("THERMAL")}
            style={{
              background: activeTab === "THERMAL" ? "rgba(239, 68, 68, 0.3)" : "transparent",
              color: activeTab === "THERMAL" ? "#f87171" : "#94a3b8",
              border: "none",
              padding: "0.25rem 0.6rem",
              borderRadius: "4px",
              fontSize: "0.72rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Thermal (EGT/CHT)
          </button>

          <button
            onClick={() => setActiveTab("PROPULSION")}
            style={{
              background: activeTab === "PROPULSION" ? "rgba(14, 165, 233, 0.3)" : "transparent",
              color: activeTab === "PROPULSION" ? "#38bdf8" : "#94a3b8",
              border: "none",
              padding: "0.25rem 0.6rem",
              borderRadius: "4px",
              fontSize: "0.72rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            RPM & Throttle
          </button>

          <button
            onClick={() => setActiveTab("FLUIDS")}
            style={{
              background: activeTab === "FLUIDS" ? "rgba(6, 182, 212, 0.3)" : "transparent",
              color: activeTab === "FLUIDS" ? "#22d3ee" : "#94a3b8",
              border: "none",
              padding: "0.25rem 0.6rem",
              borderRadius: "4px",
              fontSize: "0.72rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Fluids & Vibration
          </button>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div style={{ flex: 1, minHeight: "220px", position: "relative" }}>
        {activeTab === "HEALTH" && <Line data={healthData} options={chartOptions} />}
        {activeTab === "THERMAL" && <Line data={thermalData} options={chartOptions} />}
        {activeTab === "PROPULSION" && <Line data={propulsionData} options={propulsionOptions} />}
        {activeTab === "FLUIDS" && <Line data={fluidsData} options={chartOptions} />}
      </div>

      {/* Rolling window footer */}
      <div style={{
        marginTop: "0.5rem",
        display: "flex",
        justifyContent: "space-between",
        fontSize: "0.68rem",
        color: "var(--text-muted)",
      }}>
        <span>Rolling History: Bounded at latest {history.length} samples</span>
        <span className="mono-val">Live Delta: 0.5s intervals</span>
      </div>

    </div>
  );
};
