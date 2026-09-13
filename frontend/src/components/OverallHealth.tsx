import React from "react";
import { Flame, Gauge, Layers, ShieldCheck, Thermometer, Zap } from "lucide-react";
import type { SubsystemHealth } from "../types/api";

interface OverallHealthProps {
  health: SubsystemHealth;
}

export const OverallHealth: React.FC<OverallHealthProps> = ({ health }) => {
  const overall = Math.max(0, Math.min(100, health.overall));

  const getStatusColor = (val: number) => {
    if (val >= 80) return "var(--accent-emerald)";
    if (val >= 50) return "var(--accent-amber)";
    return "var(--accent-crimson)";
  };

  const getStatusText = (val: number) => {
    if (val >= 80) return "HEALTHY";
    if (val >= 50) return "WARNING";
    return "CRITICAL";
  };

  const circumference = 2 * Math.PI * 46;
  const strokeDashoffset = circumference - (overall / 100) * circumference;

  const subsystems = [
    { label: "Thermal Subsystem", value: health.thermal, icon: Thermometer, metric: "EGT / CHT Cooling" },
    { label: "Combustion System", value: health.combustion, icon: Flame, metric: "Air-Fuel & MAP" },
    { label: "Lubrication Subsystem", value: health.lubrication, icon: Gauge, metric: "Oil Pressure & Temp" },
    { label: "Mechanical Integrity", value: health.mechanical, icon: Layers, metric: "Vibration & RPM" },
    { label: "Electrical / Ignition", value: health.electrical, icon: Zap, metric: "Battery & Timing" },
  ];

  return (
    <div className="gcs-card" style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <ShieldCheck size={18} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.85rem", fontWeight: 700, letterSpacing: "0.04em", color: "#f8fafc" }}>
            ENGINE HEALTH MONITOR
          </span>
        </div>
        <span className={`badge badge-${getStatusText(overall).toLowerCase()}`}>
          {getStatusText(overall)}
        </span>
      </div>

      {/* Main Gauge & Subsystems Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: "1.25rem", alignItems: "center" }}>
        
        {/* Radial SVG Gauge */}
        <div style={{ position: "relative", width: "120px", height: "120px", margin: "0 auto" }}>
          <svg width="120" height="120" viewBox="0 0 120 120" style={{ transform: "rotate(-90deg)" }}>
            {/* Background Circle */}
            <circle
              cx="60"
              cy="60"
              r="46"
              fill="transparent"
              stroke="rgba(30, 41, 59, 0.8)"
              strokeWidth="8"
            />
            {/* Value Arc */}
            <circle
              cx="60"
              cy="60"
              r="46"
              fill="transparent"
              stroke={getStatusColor(overall)}
              strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              style={{ transition: "stroke-dashoffset 0.5s ease, stroke 0.4s ease" }}
            />
          </svg>

          {/* Center Text */}
          <div style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
          }}>
            <span className="mono-val" style={{ fontSize: "1.6rem", fontWeight: 800, color: "#ffffff", lineHeight: 1 }}>
              {overall.toFixed(1)}%
            </span>
            <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontWeight: 600, marginTop: "2px" }}>
              OVERALL
            </span>
          </div>
        </div>

        {/* Subsystem Health Progress Bars */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem" }}>
          {subsystems.map((sub) => {
            const Icon = sub.icon;
            const subColor = getStatusColor(sub.value);
            return (
              <div key={sub.label}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.15rem", fontSize: "0.75rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", color: "var(--text-secondary)" }}>
                    <Icon size={12} color={subColor} />
                    <span>{sub.label}</span>
                  </div>
                  <span className="mono-val" style={{ fontWeight: 700, color: subColor }}>
                    {sub.value.toFixed(1)}%
                  </span>
                </div>
                {/* Progress bar */}
                <div style={{
                  width: "100%",
                  height: "5px",
                  background: "rgba(30, 41, 59, 0.7)",
                  borderRadius: "3px",
                  overflow: "hidden",
                }}>
                  <div style={{
                    width: `${Math.max(0, Math.min(100, sub.value))}%`,
                    height: "100%",
                    background: subColor,
                    borderRadius: "3px",
                    transition: "width 0.4s ease, background-color 0.4s ease",
                  }} />
                </div>
              </div>
            );
          })}
        </div>

      </div>

      {/* Threshold indicator footer */}
      <div style={{
        marginTop: "0.75rem",
        paddingTop: "0.5rem",
        borderTop: "1px solid rgba(56, 189, 248, 0.08)",
        display: "flex",
        justifyContent: "space-between",
        fontSize: "0.68rem",
        color: "var(--text-muted)",
      }}>
        <span>Thresholds: 80-100% Healthy</span>
        <span>50-79% Warning</span>
        <span>&lt;50% Critical</span>
      </div>
    </div>
  );
};
