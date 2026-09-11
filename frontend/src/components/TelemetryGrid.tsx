import React from "react";
import {
  Activity,
  BatteryCharging,
  Droplets,
  Gauge,
  Sliders,
  Thermometer,
  Waves,
  Wind,
  Zap,
} from "lucide-react";
import type { EngineMeasurements, EnginePerformance } from "../types/api";

interface TelemetryGridProps {
  engine: EngineMeasurements;
  performance: EnginePerformance;
}

export const TelemetryGrid: React.FC<TelemetryGridProps> = ({ engine, performance }) => {
  const cards = [
    {
      label: "ENGINE SPEED",
      value: engine.rpm.toFixed(0),
      unit: "RPM",
      icon: Gauge,
      nominal: "1200 - 3200",
      status: engine.rpm < 800 ? "IDLE" : engine.rpm > 3500 ? "HIGH" : "NORMAL",
      color: "var(--accent-cyan)",
    },
    {
      label: "THROTTLE DEMAND",
      value: engine.throttle.toFixed(1),
      unit: "%",
      icon: Sliders,
      nominal: "0 - 100",
      status: "COMMAND",
      color: "var(--accent-blue)",
    },
    {
      label: "EXHAUST GAS TEMP (EGT)",
      value: engine.egt.toFixed(1),
      unit: "°C",
      icon: Thermometer,
      nominal: "550 - 750",
      status: engine.egt > 760 ? "CRITICAL" : engine.egt > 720 ? "ELEVATED" : "NORMAL",
      color: engine.egt > 760 ? "var(--accent-crimson)" : engine.egt > 720 ? "var(--accent-amber)" : "var(--accent-emerald)",
    },
    {
      label: "CYLINDER HEAD TEMP (CHT)",
      value: engine.cht.toFixed(1),
      unit: "°C",
      icon: Thermometer,
      nominal: "130 - 200",
      status: engine.cht > 210 ? "CRITICAL" : engine.cht > 190 ? "ELEVATED" : "NORMAL",
      color: engine.cht > 210 ? "var(--accent-crimson)" : engine.cht > 190 ? "var(--accent-amber)" : "var(--accent-emerald)",
    },
    {
      label: "MANIFOLD PRESSURE (MAP)",
      value: engine.manifold_absolute_pressure.toFixed(1),
      unit: "kPa",
      icon: Wind,
      nominal: "35 - 95",
      status: "BOOST",
      color: "var(--accent-cyan)",
    },
    {
      label: "OIL PRESSURE",
      value: engine.oil_pressure.toFixed(1),
      unit: "psi",
      icon: Droplets,
      nominal: "28 - 55",
      status: engine.oil_pressure < 25 ? "LOW PRESS" : "NORMAL",
      color: engine.oil_pressure < 25 ? "var(--accent-crimson)" : "var(--accent-emerald)",
    },
    {
      label: "OIL TEMPERATURE",
      value: engine.oil_temperature.toFixed(1),
      unit: "°C",
      icon: Droplets,
      nominal: "75 - 105",
      status: engine.oil_temperature > 110 ? "HIGH" : "NORMAL",
      color: engine.oil_temperature > 110 ? "var(--accent-amber)" : "var(--accent-emerald)",
    },
    {
      label: "FUEL FLOW RATE",
      value: engine.fuel_flow.toFixed(1),
      unit: "L/h",
      icon: Droplets,
      nominal: "8 - 28",
      status: "METERED",
      color: "var(--accent-cyan)",
    },
    {
      label: "ENGINE VIBRATION",
      value: engine.vibration.toFixed(2),
      unit: "mm/s",
      icon: Waves,
      nominal: "< 2.5",
      status: engine.vibration > 2.8 ? "ABNORMAL" : "NOMINAL",
      color: engine.vibration > 2.8 ? "var(--accent-crimson)" : "var(--accent-emerald)",
    },
    {
      label: "ELECTRICAL BUS",
      value: engine.battery_voltage.toFixed(2),
      unit: "V",
      icon: BatteryCharging,
      nominal: "13.2 - 14.4",
      status: engine.battery_voltage < 12.5 ? "LOW" : "NOMINAL",
      color: engine.battery_voltage < 12.5 ? "var(--accent-crimson)" : "var(--accent-emerald)",
    },
    {
      label: "ESTIMATED POWER",
      value: (performance.estimated_power / 1000).toFixed(1),
      unit: "kW",
      icon: Zap,
      nominal: "0 - 85",
      status: `LOAD: ${performance.engine_load.toFixed(0)}%`,
      color: "var(--accent-purple)",
    },
    {
      label: "ESTIMATED TORQUE",
      value: performance.estimated_torque.toFixed(1),
      unit: "Nm",
      icon: Activity,
      nominal: "50 - 150",
      status: `EFF: ${performance.fuel_efficiency.toFixed(0)}%`,
      color: "var(--accent-purple)",
    },
  ];

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
      gap: "0.85rem",
      marginBottom: "1rem",
    }}>
      {cards.map((c) => {
        const Icon = c.icon;
        return (
          <div
            key={c.label}
            className="gcs-card"
            style={{
              padding: "0.85rem 1rem",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            {/* Top Label & Icon */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
              <span style={{ fontSize: "0.68rem", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.03em" }}>
                {c.label}
              </span>
              <Icon size={14} color={c.color} />
            </div>

            {/* Main Value & Unit */}
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.35rem", margin: "0.2rem 0" }}>
              <span className="mono-val" style={{ fontSize: "1.45rem", fontWeight: 800, color: "#f8fafc" }}>
                {c.value}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>
                {c.unit}
              </span>
            </div>

            {/* Nominal Range & Status Badge */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.3rem", fontSize: "0.68rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Band: {c.nominal}</span>
              <span style={{
                color: c.color,
                fontWeight: 700,
                background: "rgba(15, 23, 42, 0.8)",
                padding: "0.1rem 0.35rem",
                borderRadius: "4px",
                border: "1px solid rgba(255, 255, 255, 0.08)",
              }}>
                {c.status}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
