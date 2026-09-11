import React, { useState } from "react";
import { AlertTriangle, Play, RefreshCw, RotateCcw, ShieldCheck, Sliders, StepForward, Zap } from "lucide-react";

interface SimulationControlsProps {
  currentThrottle: number;
  activeFault?: string | null;
  onSetThrottle: (throttle: number) => void;
  onStartSimulation: (throttle: number) => void;
  onStepSimulation: (dt: number) => void;
  onInjectFault: (faultType: string | null) => void;
  onResetSimulation: () => void;
  onRunDemoFlow: () => void;
  isDemoRunning: boolean;
}

const FAULT_TYPES = [
  { value: "OVERHEATING", label: "OVERHEATING (Thermal stress / cooling failure)" },
  { value: "LUBRICATION_FAILURE", label: "LUBRICATION_FAILURE (Oil pressure drop)" },
  { value: "INJECTOR_DEGRADATION", label: "INJECTOR_DEGRADATION (Fuel delivery imbalance)" },
  { value: "MISFIRE", label: "MISFIRE (Combustion power loss)" },
  { value: "COMBUSTION_INSTABILITY", label: "COMBUSTION_INSTABILITY (Pressure oscillations)" },
  { value: "ABNORMAL_VIBRATION", label: "ABNORMAL_VIBRATION (Mechanical bearing/prop wear)" },
  { value: "SENSOR_DRIFT", label: "SENSOR_DRIFT (Instrument sensor drift)" },
  { value: "SENSOR_FAILURE", label: "SENSOR_FAILURE (Sensor stuck / disconnection)" },
];

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  currentThrottle,
  activeFault,
  onSetThrottle,
  onStartSimulation,
  onStepSimulation,
  onInjectFault,
  onResetSimulation,
  onRunDemoFlow,
  isDemoRunning,
}) => {
  const [selectedFault, setSelectedFault] = useState<string>("OVERHEATING");
  const [localThrottle, setLocalThrottle] = useState<number>(currentThrottle || 45);

  const handleThrottleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setLocalThrottle(val);
  };

  const handleThrottleCommit = () => {
    onSetThrottle(localThrottle);
  };

  return (
    <div className="gcs-card" style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.6rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Sliders size={18} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.85rem", fontWeight: 700, letterSpacing: "0.04em", color: "#f8fafc" }}>
            SYNTHETIC SIMULATOR & FAULT INJECTION CONTROLS
          </span>
        </div>

        <button
          onClick={onRunDemoFlow}
          disabled={isDemoRunning}
          className="btn-aerotwin"
          style={{ fontSize: "0.72rem", padding: "0.25rem 0.6rem" }}
        >
          {isDemoRunning ? <RefreshCw size={12} className="animate-spin" /> : <Zap size={12} />}
          <span>{isDemoRunning ? "Demo Active" : "Run Demo Sequence"}</span>
        </button>
      </div>

      {/* Throttle Slider & Stepping */}
      <div style={{
        background: "rgba(15, 23, 42, 0.6)",
        padding: "0.65rem 0.85rem",
        borderRadius: "8px",
        border: "1px solid var(--border-subtle)",
        marginBottom: "0.65rem",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.3rem" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
            Engine Throttle Position
          </span>
          <span className="mono-val" style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--accent-cyan)" }}>
            {localThrottle.toFixed(0)}%
          </span>
        </div>

        <input
          type="range"
          min="0"
          max="100"
          value={localThrottle}
          onChange={handleThrottleChange}
          onMouseUp={handleThrottleCommit}
          onTouchEnd={handleThrottleCommit}
          style={{
            width: "100%",
            accentColor: "var(--accent-cyan)",
            cursor: "pointer",
            marginBottom: "0.5rem",
          }}
        />

        {/* Action Buttons */}
        <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
          <button
            onClick={() => onStartSimulation(localThrottle)}
            className="btn-secondary"
            style={{ fontSize: "0.72rem", padding: "0.3rem 0.6rem", display: "flex", alignItems: "center", gap: "0.3rem" }}
          >
            <Play size={12} />
            <span>Init Flight</span>
          </button>

          <button
            onClick={() => onStepSimulation(0.5)}
            className="btn-secondary"
            style={{ fontSize: "0.72rem", padding: "0.3rem 0.6rem", display: "flex", alignItems: "center", gap: "0.3rem" }}
          >
            <StepForward size={12} />
            <span>Step (0.5s)</span>
          </button>

          <button
            onClick={onResetSimulation}
            className="btn-secondary"
            style={{ fontSize: "0.72rem", padding: "0.3rem 0.6rem", display: "flex", alignItems: "center", gap: "0.3rem" }}
          >
            <RotateCcw size={12} />
            <span>Reset DT</span>
          </button>
        </div>
      </div>

      {/* Fault Injection Section */}
      <div style={{
        background: activeFault ? "rgba(239, 68, 68, 0.1)" : "rgba(15, 23, 42, 0.6)",
        padding: "0.65rem 0.85rem",
        borderRadius: "8px",
        border: `1px solid ${activeFault ? "rgba(239, 68, 68, 0.3)" : "var(--border-subtle)"}`,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
            Synthetic Fault Injection
          </span>
          {activeFault ? (
            <span className="badge badge-critical" style={{ fontSize: "0.65rem" }}>
              ACTIVE: {activeFault}
            </span>
          ) : (
            <span className="badge badge-healthy" style={{ fontSize: "0.65rem" }}>
              CLEARED
            </span>
          )}
        </div>

        <div style={{ display: "flex", gap: "0.4rem", alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={selectedFault}
            onChange={(e) => setSelectedFault(e.target.value)}
            style={{
              flex: 1,
              minWidth: "150px",
              background: "rgba(15, 23, 42, 0.9)",
              color: "#f8fafc",
              border: "1px solid var(--border-active)",
              borderRadius: "6px",
              padding: "0.3rem 0.5rem",
              fontSize: "0.72rem",
              cursor: "pointer",
              outline: "none",
            }}
          >
            {FAULT_TYPES.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>

          <button
            onClick={() => onInjectFault(selectedFault)}
            className="btn-fault"
            style={{ fontSize: "0.72rem", padding: "0.3rem 0.65rem" }}
          >
            <AlertTriangle size={12} />
            <span>Inject</span>
          </button>

          <button
            onClick={() => onInjectFault(null)}
            className="btn-secondary"
            style={{ fontSize: "0.72rem", padding: "0.3rem 0.65rem" }}
          >
            <ShieldCheck size={12} />
            <span>Clear</span>
          </button>
        </div>
      </div>

    </div>
  );
};
