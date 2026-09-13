import React from "react";
import { Wrench } from "lucide-react";
import type { DashboardAnalytics, SubsystemHealth } from "../types/api";

interface MaintenanceAdvisoryProps {
  analytics: DashboardAnalytics;
  health: SubsystemHealth;
}

export const MaintenanceAdvisory: React.FC<MaintenanceAdvisoryProps> = ({ analytics, health }) => {
  const { faults, degradation, rul } = analytics;
  const activeFault = faults && faults.length > 0 ? faults[0] : null;

  // Determine advisory level & actionable directives
  let level: "NORMAL" | "MONITOR" | "INSPECT_SOON" | "CRITICAL" = "NORMAL";
  let title = "Routine Maintenance Nominal";
  let recommendation = "All subsystem health scores within operating tolerances. Maintain standard flight-hour service intervals.";
  let subsystemTarget = "General Propulsion System";

  if (activeFault) {
    level = "CRITICAL";
    if (activeFault.fault_type === "OVERHEATING") {
      title = "CRITICAL: Thermal Overheat Detected";
      recommendation = "Immediate post-flight cylinder head inspection required. Check oil cooler airflow, cowling intake, and cylinder temperature sensors.";
      subsystemTarget = "Thermal & Cooling System";
    } else if (activeFault.fault_type === "LUBRICATION_FAILURE") {
      title = "CRITICAL: Lubrication Failure Alert";
      recommendation = "Emergency inspection of engine oil levels, pressure relief valve, and main oil pump. Perform oil filter debris particulate analysis.";
      subsystemTarget = "Lubrication Subsystem";
    } else if (activeFault.fault_type === "INJECTOR_DEGRADATION") {
      title = "WARNING: Fuel Injector Degradation";
      recommendation = "Fuel flow deviation flagged. Inspect injector spray pattern, clean injector nozzles with ultrasonic bath, and calibrate electronic fuel controller.";
      subsystemTarget = "Fuel & Injection Assembly";
    } else {
      title = `CRITICAL: Active Fault - ${activeFault.fault_type}`;
      recommendation = `Propulsion engineer intervention required to diagnose ${activeFault.fault_type}. Ground UAV until clear test bench validation.`;
      subsystemTarget = "Propulsion Engineering";
    }
  } else if (health.thermal < 75) {
    level = "INSPECT_SOON";
    title = "Thermal Subsystem Stress";
    recommendation = "Operating temperatures elevated. Inspect cooling fins and clean oil radiator prior to subsequent sorties.";
    subsystemTarget = "Thermal Management";
  } else if (health.lubrication < 75) {
    level = "INSPECT_SOON";
    title = "Lubrication Health Degrading";
    recommendation = "Oil pressure below nominal cruise baseline. Top up synthetic engine oil and inspect line fittings.";
    subsystemTarget = "Lubrication Assembly";
  } else if (degradation.trend === "WORSENING" || degradation.degradation_index > 0.15) {
    level = "MONITOR";
    title = "Accelerated Wear Trend Flagged";
    recommendation = "AI degradation model shows accelerating trend. Schedule non-destructive inspection within 15 flight hours.";
    subsystemTarget = "Mechanical Power Train";
  }

  const getLevelBadge = () => {
    switch (level) {
      case "CRITICAL":
        return <span className="badge badge-critical">CRITICAL ACTION REQUIRED</span>;
      case "INSPECT_SOON":
        return <span className="badge badge-warning">INSPECT SOON</span>;
      case "MONITOR":
        return <span className="badge badge-warning">MONITOR TREND</span>;
      default:
        return <span className="badge badge-healthy">NOMINAL SERVICE</span>;
    }
  };

  return (
    <div className="gcs-card" style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.6rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Wrench size={18} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.85rem", fontWeight: 700, letterSpacing: "0.04em", color: "#f8fafc" }}>
            PROTOTYPE MAINTENANCE ADVISORY
          </span>
        </div>
        {getLevelBadge()}
      </div>

      {/* Advisory Card Body */}
      <div style={{
        background: level === "CRITICAL" ? "rgba(239, 68, 68, 0.1)" : "rgba(15, 23, 42, 0.6)",
        border: `1px solid ${level === "CRITICAL" ? "rgba(239, 68, 68, 0.3)" : "var(--border-subtle)"}`,
        borderRadius: "8px",
        padding: "0.85rem 1rem",
      }}>
        <div style={{ fontSize: "0.92rem", fontWeight: 700, color: level === "CRITICAL" ? "#fca5a5" : "#f1f5f9", marginBottom: "0.35rem" }}>
          {title}
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>
          {recommendation}
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginTop: "0.6rem", fontSize: "0.72rem", color: "var(--text-muted)" }}>
          <div>
            Target Component: <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{subsystemTarget}</span>
          </div>
          <div>
            RUL Estimation: <span className="mono-val" style={{ color: "var(--text-primary)", fontWeight: 600 }}>{rul.status}</span>
          </div>
        </div>
      </div>

      {/* Engineering Footer */}
      <div style={{
        marginTop: "0.6rem",
        fontSize: "0.68rem",
        color: "var(--text-muted)",
        display: "flex",
        justifyContent: "space-between",
      }}>
        <span>Maintenance Guideline: UAV Ground Crew Operations Manual</span>
        <span>Advisory Engine: AI Predictive Model</span>
      </div>

    </div>
  );
};
