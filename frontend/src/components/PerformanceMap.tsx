import React, { useMemo, useState } from "react";
import { Compass, Info } from "lucide-react";
import type { PerformanceMapResponse } from "../types/api";

interface PerformanceMapProps {
  performanceMap: PerformanceMapResponse | null;
}

type MetricKey = "engine_load" | "torque_nm" | "power_kw" | "fuel_efficiency" | "fuel_flow";

export const PerformanceMap: React.FC<PerformanceMapProps> = ({ performanceMap }) => {
  const [metric, setMetric] = useState<MetricKey>("engine_load");

  const metricConfigs: Record<MetricKey, { label: string; unit: string; max: number; min: number }> = {
    engine_load: { label: "Engine Load", unit: "%", min: 0, max: 100 },
    torque_nm: { label: "Estimated Torque", unit: "Nm", min: 0, max: 160 },
    power_kw: { label: "Estimated Power", unit: "kW", min: 0, max: 90 },
    fuel_efficiency: { label: "Fuel Efficiency", unit: "%", min: 0, max: 100 },
    fuel_flow: { label: "Fuel Flow", unit: "L/h", min: 0, max: 35 },
  };

  const currentCfg = metricConfigs[metric];

  // SVG coordinate dimensions
  const width = 540;
  const height = 240;
  const padLeft = 55;
  const padRight = 30;
  const padTop = 25;
  const padBottom = 35;

  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const minRPM = 800;
  const maxRPM = 5200;

  const scaleX = (rpm: number) => {
    const clamped = Math.max(minRPM, Math.min(maxRPM, rpm));
    return padLeft + ((clamped - minRPM) / (maxRPM - minRPM)) * plotW;
  };

  const scaleY = (val: number) => {
    const clamped = Math.max(currentCfg.min, Math.min(currentCfg.max, val));
    return padTop + plotH - ((clamped - currentCfg.min) / (currentCfg.max - currentCfg.min)) * plotH;
  };

  // Color generator for envelope nodes
  const getNodeColor = (val: number) => {
    const ratio = Math.max(0, Math.min(1, (val - currentCfg.min) / (currentCfg.max - currentCfg.min)));
    if (ratio < 0.35) return "#0ea5e9";
    if (ratio < 0.7) return "#10b981";
    if (ratio < 0.88) return "#f59e0b";
    return "#ef4444";
  };

  const envelopePoints = performanceMap?.envelope_grid || [];
  const observedPoints = performanceMap?.observed_points || [];
  const currentPt = performanceMap?.current_point;

  // Build path string for observed points
  const observedPath = useMemo(() => {
    if (observedPoints.length < 2) return "";
    return observedPoints
      .map((pt, i) => {
        const x = scaleX(pt.rpm);
        const y = scaleY(pt[metric]);
        return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" ");
  }, [observedPoints, metric]);

  return (
    <div className="gcs-card" style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      
      {/* Header & Metric Selector */}
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem", gap: "0.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Compass size={18} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.85rem", fontWeight: 700, letterSpacing: "0.04em", color: "#f8fafc" }}>
            ENGINE PERFORMANCE MAP (SIMULATED ENVELOPE)
          </span>
        </div>

        {/* Metric Switcher Dropdown */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Dimension:</span>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as MetricKey)}
            style={{
              background: "rgba(15, 23, 42, 0.9)",
              color: "var(--accent-cyan)",
              border: "1px solid var(--border-active)",
              borderRadius: "5px",
              padding: "0.2rem 0.5rem",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
              outline: "none",
            }}
          >
            <option value="engine_load">Engine Load (%)</option>
            <option value="torque_nm">Torque (Nm)</option>
            <option value="power_kw">Power (kW)</option>
            <option value="fuel_efficiency">Fuel Efficiency (%)</option>
            <option value="fuel_flow">Fuel Flow (L/h)</option>
          </select>
        </div>
      </div>

      {/* SVG 2D Coordinate Map */}
      <div style={{ width: "100%", position: "relative", overflowX: "auto" }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", maxHeight: "240px" }}>
          {/* Background Grid Lines */}
          {[1000, 2000, 3000, 4000, 5000].map((r) => {
            const x = scaleX(r);
            return (
              <g key={r}>
                <line x1={x} y1={padTop} x2={x} y2={padTop + plotH} stroke="rgba(255, 255, 255, 0.06)" strokeDasharray="3 3" />
                <text x={x} y={padTop + plotH + 15} fill="#64748b" fontSize="9" textAnchor="middle" fontFamily="var(--font-mono)">
                  {r}
                </text>
              </g>
            );
          })}

          {/* Y Axis Grid Lines */}
          {[0.25, 0.5, 0.75, 1.0].map((ratio) => {
            const val = currentCfg.min + ratio * (currentCfg.max - currentCfg.min);
            const y = scaleY(val);
            return (
              <g key={ratio}>
                <line x1={padLeft} y1={y} x2={padLeft + plotW} y2={y} stroke="rgba(255, 255, 255, 0.06)" strokeDasharray="3 3" />
                <text x={padLeft - 8} y={y + 3} fill="#64748b" fontSize="9" textAnchor="end" fontFamily="var(--font-mono)">
                  {val.toFixed(0)}
                </text>
              </g>
            );
          })}

          {/* Axes labels */}
          <text x={padLeft + plotW / 2} y={height - 5} fill="#94a3b8" fontSize="10" textAnchor="middle" fontWeight="bold">
            Engine Speed (RPM)
          </text>
          <text
            x={15}
            y={padTop + plotH / 2}
            fill="#94a3b8"
            fontSize="10"
            textAnchor="middle"
            fontWeight="bold"
            transform={`rotate(-90 15 ${padTop + plotH / 2})`}
          >
            {currentCfg.label} ({currentCfg.unit})
          </text>

          {/* Envelope Grid Nodes */}
          {envelopePoints.map((pt, i) => {
            const x = scaleX(pt.rpm);
            const y = scaleY(pt[metric]);
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={2.5}
                fill={getNodeColor(pt[metric])}
                opacity={0.4}
              />
            );
          })}

          {/* Flight History Track */}
          {observedPath && (
            <path
              d={observedPath}
              fill="none"
              stroke="rgba(56, 189, 248, 0.7)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Current Active Operating Point Marker with Crosshairs */}
          {currentPt && (
            <g>
              {/* Horizontal / Vertical Hairlines */}
              <line
                x1={padLeft}
                y1={scaleY(currentPt[metric])}
                x2={padLeft + plotW}
                y2={scaleY(currentPt[metric])}
                stroke="rgba(56, 189, 248, 0.4)"
                strokeDasharray="2 2"
              />
              <line
                x1={scaleX(currentPt.rpm)}
                y1={padTop}
                x2={scaleX(currentPt.rpm)}
                y2={padTop + plotH}
                stroke="rgba(56, 189, 248, 0.4)"
                strokeDasharray="2 2"
              />

              {/* Pulsing Target Point */}
              <circle
                cx={scaleX(currentPt.rpm)}
                cy={scaleY(currentPt[metric])}
                r={8}
                fill="none"
                stroke="#38bdf8"
                strokeWidth="1.5"
                opacity={0.8}
              >
                <animate attributeName="r" values="5;10;5" dur="1.8s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.9;0.2;0.9" dur="1.8s" repeatCount="indefinite" />
              </circle>
              <circle
                cx={scaleX(currentPt.rpm)}
                cy={scaleY(currentPt[metric])}
                r={4}
                fill="#ffffff"
                stroke="#0284c7"
                strokeWidth="2"
              />
            </g>
          )}
        </svg>
      </div>

      {/* Real-time Readout & Mandatory Engineering Disclaimer */}
      <div style={{
        marginTop: "0.5rem",
        paddingTop: "0.45rem",
        borderTop: "1px solid rgba(56, 189, 248, 0.08)",
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: "0.72rem",
        color: "var(--text-muted)",
        gap: "0.5rem",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ color: "var(--text-secondary)" }}>Operating Point:</span>
          {currentPt ? (
            <span className="mono-val" style={{ color: "var(--accent-cyan)", fontWeight: 700 }}>
              {currentPt.rpm.toFixed(0)} RPM | {currentPt[metric].toFixed(1)} {currentCfg.unit}
            </span>
          ) : (
            <span>Standing by</span>
          )}
        </div>

        {/* Aerospace disclaimer as required in specification */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontStyle: "italic", color: "#64748b" }}>
          <Info size={12} color="var(--accent-cyan)" />
          <span>Prototype digital twin simulation envelope; not certified aircraft-engine calibration data.</span>
        </div>
      </div>

    </div>
  );
};
