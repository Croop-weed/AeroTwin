import React from "react";
import { Header } from "./components/Header";
import { OverallHealth } from "./components/OverallHealth";
import { TelemetryGrid } from "./components/TelemetryGrid";
import { FaultAlerts } from "./components/FaultAlerts";
import { LiveCharts } from "./components/LiveCharts";
import { PerformanceMap } from "./components/PerformanceMap";
import { SimulationControls } from "./components/SimulationControls";
import { MaintenanceAdvisory } from "./components/MaintenanceAdvisory";
import { MissionReport } from "./components/MissionReport";
import { useDigitalTwin } from "./hooks/useDigitalTwin";
import { AlertCircle, ExternalLink } from "lucide-react";
import { API_BASE } from "./services/api";

export const App: React.FC = () => {
  const {
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
    isDemoRunning,
    demoStage,
    startSimulation,
    stepSimulation,
    setThrottle,
    injectFault,
    resetSimulation,
    refreshMissionReport,
    runDemoFlow,
  } = useDigitalTwin("UAV-001");

  return (
    <div style={{ padding: "1rem 1.25rem", maxWidth: "1680px", margin: "0 auto" }}>
      {/* Top GCS Header */}
      <Header
        uavId={uavId}
        onSelectUAV={setUavId}
        uavList={uavList}
        uavInfo={snapshot?.uav}
        status={status}
        isDemoRunning={isDemoRunning}
        demoStage={demoStage}
        onRunDemo={runDemoFlow}
        overallHealth={snapshot?.health?.overall}
      />

      {/* Error Alert (if backend disconnected or call failed) */}
      {error && (
        <div style={{
          background: "rgba(239, 68, 68, 0.15)",
          border: "1px solid rgba(239, 68, 68, 0.4)",
          borderRadius: "8px",
          padding: "0.75rem 1rem",
          marginBottom: "1rem",
          display: "flex",
          alignItems: "center",
          gap: "0.6rem",
          fontSize: "0.85rem",
          color: "#fca5a5",
        }}>
          <AlertCircle size={18} color="var(--accent-crimson)" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading state before first snapshot */}
      {loading && !snapshot ? (
        <div className="gcs-card" style={{ textAlign: "center", padding: "3rem" }}>
          <div className="pulse-connecting" style={{ width: "16px", height: "16px", margin: "0 auto 1rem auto" }} />
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--accent-cyan)" }}>
            Connecting to AeroTwin Digital Twin Backend ({uavId})...
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            Querying REST endpoint and establishing real-time telemetry WebSocket stream...
          </div>
        </div>
      ) : snapshot ? (
        <>
          {/* Section 1: Live Engine Telemetry Grid (12 cards) */}
          <TelemetryGrid engine={snapshot.engine} performance={snapshot.performance} />

          {/* Section 2: Health Overview & Active Fault Prediction */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(12, 1fr)",
            gap: "1rem",
            marginBottom: "1rem",
          }}>
            <div style={{ gridColumn: "span 4" }} className="lg:col-span-4 sm:col-span-12">
              <OverallHealth health={snapshot.health} />
            </div>
            <div style={{ gridColumn: "span 8" }} className="lg:col-span-8 sm:col-span-12">
              <FaultAlerts analytics={snapshot.analytics} />
            </div>
          </div>

          {/* Section 3: Live Time-Series Charts & Engine Performance Map */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(12, 1fr)",
            gap: "1rem",
            marginBottom: "1rem",
          }}>
            <div style={{ gridColumn: "span 7" }} className="lg:col-span-7 sm:col-span-12">
              <LiveCharts history={history} />
            </div>
            <div style={{ gridColumn: "span 5" }} className="lg:col-span-5 sm:col-span-12">
              <PerformanceMap performanceMap={performanceMap} />
            </div>
          </div>

          {/* Section 4: Simulation Controls, Maintenance Advisory, Mission Health */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(12, 1fr)",
            gap: "1rem",
            marginBottom: "1rem",
          }}>
            <div style={{ gridColumn: "span 4" }} className="lg:col-span-4 sm:col-span-12">
              <SimulationControls
                currentThrottle={snapshot.engine.throttle}
                activeFault={snapshot.analytics.faults[0]?.fault_type}
                onSetThrottle={setThrottle}
                onStartSimulation={startSimulation}
                onStepSimulation={stepSimulation}
                onInjectFault={injectFault}
                onResetSimulation={resetSimulation}
                onRunDemoFlow={runDemoFlow}
                isDemoRunning={isDemoRunning}
              />
            </div>
            <div style={{ gridColumn: "span 4" }} className="lg:col-span-4 sm:col-span-12">
              <MaintenanceAdvisory analytics={snapshot.analytics} health={snapshot.health} />
            </div>
            <div style={{ gridColumn: "span 4" }} className="lg:col-span-4 sm:col-span-12">
              <MissionReport report={missionReport} onRefresh={refreshMissionReport} />
            </div>
          </div>
        </>
      ) : null}

      {/* Footer */}
      <footer style={{
        marginTop: "1.5rem",
        paddingTop: "1rem",
        borderTop: "1px solid rgba(56, 189, 248, 0.1)",
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: "0.75rem",
        color: "var(--text-muted)",
        gap: "1rem",
      }}>
        <div>
          <span>AeroTwin Digital Twin System | Smart India Hackathon Prototype</span>
          <span style={{ margin: "0 0.5rem" }}>•</span>
          <span>Backend Target: </span>
          <span className="mono-val" style={{ color: "var(--accent-cyan)" }}>{API_BASE}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <a
            href={`${API_BASE}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--text-secondary)", textDecoration: "none", display: "flex", alignItems: "center", gap: "0.3rem" }}
          >
            <span>FastAPI Swagger Docs</span>
            <ExternalLink size={12} />
          </a>
          <a
            href={`${API_BASE}/health`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--text-secondary)", textDecoration: "none", display: "flex", alignItems: "center", gap: "0.3rem" }}
          >
            <span>Health Endpoint</span>
            <ExternalLink size={12} />
          </a>
        </div>
      </footer>
    </div>
  );
};

export default App;
