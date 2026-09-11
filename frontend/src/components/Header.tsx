import React from "react";
import { Activity, Plane, Play, RefreshCw } from "lucide-react";
import type { ConnectionStatus } from "../services/websocket";
import type { UAVItem, UAVInfo } from "../types/api";

interface HeaderProps {
  uavId: string;
  onSelectUAV: (id: string) => void;
  uavList: UAVItem[];
  uavInfo?: UAVInfo;
  status: ConnectionStatus;
  isDemoRunning: boolean;
  demoStage: string;
  onRunDemo: () => void;
  overallHealth?: number;
}

export const Header: React.FC<HeaderProps> = ({
  uavId,
  onSelectUAV,
  uavList,
  uavInfo,
  status,
  isDemoRunning,
  demoStage,
  onRunDemo,
  overallHealth = 100,
}) => {
  const [time, setTime] = React.useState<string>(new Date().toISOString().substring(11, 19) + " UTC");

  React.useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toISOString().substring(11, 19) + " UTC");
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const getHealthBadge = () => {
    if (overallHealth >= 80) return <span className="badge badge-healthy">HEALTHY</span>;
    if (overallHealth >= 50) return <span className="badge badge-warning">WARNING</span>;
    return <span className="badge badge-critical">CRITICAL</span>;
  };

  return (
    <header className="gcs-card" style={{ padding: "0.85rem 1.25rem", marginBottom: "1rem" }}>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "1rem" }}>
        
        {/* Brand & Project Identity */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{
            width: "38px",
            height: "38px",
            borderRadius: "8px",
            background: "linear-gradient(135deg, #0284c7, #0369a1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 15px rgba(14, 165, 233, 0.4)",
          }}>
            <Plane size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontSize: "1.15rem", fontWeight: "800", letterSpacing: "0.05em", color: "#f8fafc" }}>
                AEROTWIN
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--accent-cyan)", background: "rgba(56, 189, 248, 0.1)", padding: "0.1rem 0.4rem", borderRadius: "4px", border: "1px solid rgba(56, 189, 248, 0.2)" }}>
                SIH DIGITAL TWIN GCS
              </span>
            </div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "1px" }}>
              MALE UAV Propulsion Health & Fault Monitoring System
            </div>
          </div>
        </div>

        {/* Center: UAV Selector & Engine Info */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>UAV:</span>
            <select
              value={uavId}
              onChange={(e) => onSelectUAV(e.target.value)}
              style={{
                background: "rgba(15, 23, 42, 0.9)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-active)",
                borderRadius: "6px",
                padding: "0.35rem 0.75rem",
                fontSize: "0.85rem",
                fontFamily: "var(--font-mono)",
                fontWeight: "600",
                cursor: "pointer",
                outline: "none",
              }}
            >
              {uavList.map((u) => (
                <option key={u.uav_id} value={u.uav_id}>
                  {u.uav_id} ({u.engine_id || "ENG-DEFAULT"})
                </option>
              ))}
              {!uavList.some((u) => u.uav_id === uavId) && (
                <option value={uavId}>{uavId}</option>
              )}
            </select>
          </div>

          <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span>ENGINE:</span>
            <span className="mono-val" style={{ color: "#e2e8f0", fontWeight: 600 }}>
              {uavInfo?.engine_id || "ROTAX-914-TURBO"}
            </span>
          </div>

          {getHealthBadge()}
        </div>

        {/* Right: Live Connection Indicator & Demo Launcher */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          
          {/* UTC Clock */}
          <div className="mono-val" style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
            {time}
          </div>

          {/* Connection Pill */}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "0.45rem",
            background: "rgba(15, 23, 42, 0.6)",
            padding: "0.3rem 0.65rem",
            borderRadius: "6px",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.75rem",
            fontWeight: 600,
          }}>
            {status === "LIVE" ? (
              <>
                <span className="pulse-live" />
                <span style={{ color: "var(--accent-emerald)" }}>LIVE STREAM</span>
              </>
            ) : status === "CONNECTING" ? (
              <>
                <span className="pulse-connecting" />
                <span style={{ color: "var(--accent-amber)" }}>CONNECTING</span>
              </>
            ) : (
              <>
                <span className="pulse-disconnected" />
                <span style={{ color: "var(--accent-crimson)" }}>OFFLINE</span>
              </>
            )}
          </div>

          {/* 3-Stage Demo Button */}
          <button
            onClick={onRunDemo}
            disabled={isDemoRunning}
            className="btn-aerotwin"
            style={{ fontSize: "0.8rem", padding: "0.4rem 0.85rem" }}
            title="Runs automated Stage 1 (Cruise) -> Stage 2 (Overheating Fault) -> Stage 3 (Recovery) demonstration"
          >
            {isDemoRunning ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                <span>DEMO RUNNING...</span>
              </>
            ) : (
              <>
                <Play size={14} fill="#ffffff" />
                <span>START DEMO SCENARIO</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Demo Stage Banner (if active) */}
      {isDemoRunning && demoStage && (
        <div style={{
          marginTop: "0.65rem",
          padding: "0.4rem 0.8rem",
          background: "rgba(14, 165, 233, 0.15)",
          border: "1px solid rgba(56, 189, 248, 0.4)",
          borderRadius: "6px",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          fontSize: "0.8rem",
          color: "var(--accent-cyan)",
          fontWeight: 600,
        }}>
          <Activity size={16} />
          <span>{demoStage}</span>
        </div>
      )}
    </header>
  );
};
