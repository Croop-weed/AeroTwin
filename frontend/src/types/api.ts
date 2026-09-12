export interface UAVInfo {
  uav_id: string;
  engine_id: string;
  status: string;
  model_type: string;
}

export interface EngineMeasurements {
  rpm: number;
  throttle: number;
  manifold_absolute_pressure: number;
  egt: number;
  cht: number;
  intake_air_temperature: number;
  ambient_temperature: number;
  oil_pressure: number;
  oil_temperature: number;
  fuel_flow: number;
  injection_timing_deg: number;
  vibration: number;
  ambient_pressure: number;
  battery_voltage: number;
}

export interface EnginePerformance {
  estimated_torque: number;
  estimated_power: number;
  engine_load: number;
  fuel_efficiency: number;
  operating_time_seconds: number;
}

export interface SubsystemHealth {
  overall: number;
  combustion: number;
  thermal: number;
  lubrication: number;
  mechanical: number;
  electrical: number;
}

export interface TemporalRates {
  previous_rpm: number;
  rpm_rate: number;
  egt_rate: number;
  cht_rate: number;
  oil_temperature_rate: number;
  vibration_rate: number;
}

export interface OperatingConditions {
  rpm_ratio: number;
  throttle_ratio: number;
  map_ratio: number;
  fuel_flow_ratio: number;
}

export interface AnomalyOutput {
  is_anomaly: boolean;
  score: number;
  confidence: number;
  timestamp?: string;
}

export interface FaultDiagnosisItem {
  fault_type: string;
  confidence: number;
  severity: number;
  evidence: Record<string, any>;
  timestamp?: string;
}

export interface DegradationOutput {
  degradation_index: number;
  confidence: number;
  trend: string;
  timestamp?: string;
}

export interface RULOutput {
  status: "AVAILABLE" | "INSUFFICIENT_DATA" | "NOT_TRAINED" | "UNAVAILABLE" | string;
  remaining_useful_life: number | null;
  lower_bound?: number | null;
  upper_bound?: number | null;
  confidence: number;
  timestamp?: string;
}

export interface SensorStatusItem {
  sensor_name: string;
  status: string;
  confidence: number;
  anomaly_score: number;
  timestamp?: string;
}

export interface DashboardAnalytics {
  anomaly: AnomalyOutput;
  faults: FaultDiagnosisItem[];
  degradation: DegradationOutput;
  rul: RULOutput;
  sensors: SensorStatusItem[];
}

export interface DashboardSnapshotResponse {
  uav: UAVInfo;
  timestamp: string;
  engine: EngineMeasurements;
  performance: EnginePerformance;
  temporal: TemporalRates;
  health: SubsystemHealth;
  analytics: DashboardAnalytics;
  operating_conditions: OperatingConditions;
}

export interface HistoryPoint {
  timestamp: string;
  measurements: EngineMeasurements;
  performance?: EnginePerformance;
  health: SubsystemHealth;
  overall_health: number;
  is_anomaly: boolean;
  anomaly_score: number;
  active_fault?: string | null;
  degradation_index: number;
  rul_estimate?: number | null;
}

export interface HistoryResponse {
  uav_id: string;
  total_points: number;
  points: HistoryPoint[];
}

export interface MissionEvent {
  timestamp: string;
  event_type: string;
  description: string;
  severity: "INFO" | "WARNING" | "CRITICAL" | string;
  details?: Record<string, any>;
}

export interface MissionReportResponse {
  mission_id: string;
  uav_id: string;
  engine_id: string;
  start_time: string | null;
  end_time: string | null;
  duration_seconds: number;
  operating_time_seconds: number;
  total_telemetry_points: number;
  average_health: number;
  min_health: number;
  max_health: number;
  anomalies_detected: number;
  fault_events_count: number;
  active_fault: string | null;
  degradation_trend: string;
  current_degradation_index: number;
  maintenance_advisory: string;
  timeline_events: MissionEvent[];
}

export interface PerformanceOperatingPoint {
  rpm: number;
  throttle: number;
  engine_load: number;
  torque_nm: number;
  power_kw: number;
  fuel_flow: number;
  fuel_efficiency: number;
}

export interface PerformanceMapResponse {
  uav_id: string;
  engine_id: string;
  envelope_grid: PerformanceOperatingPoint[];
  observed_points: PerformanceOperatingPoint[];
  current_point?: PerformanceOperatingPoint | null;
  disclaimer: string;
}

export interface UAVItem {
  uav_id: string;
  engine_id: string;
  model_type: string;
  created_at: string;
  status: string;
  telemetry_count: number;
  metadata: Record<string, any>;
}
