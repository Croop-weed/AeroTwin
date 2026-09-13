using System;

namespace AeroTwin.Networking
{
    [Serializable]
    public sealed class RegistrationMap
    {
    }

    [Serializable]
    public sealed class UavRegistrationRequest
    {
        public string uav_id;
        public string engine_id;
        public string model_type;
        public RegistrationMap configuration;
        public RegistrationMap metadata;
    }

    [Serializable]
    public sealed class TelemetryRequest
    {
        public string timestamp;
        public float rpm;
        public float throttle;
        public float manifold_absolute_pressure;
        public float egt;
        public float cht;
        public float intake_air_temperature;
        public float ambient_temperature;
        public float oil_pressure;
        public float oil_temperature;
        public float fuel_flow;
        public float injection_timing_deg;
        public float vibration;
        public float ambient_pressure;
        public float battery_voltage;
    }

    [Serializable]
    public sealed class TelemetryIngestResponse
    {
        public string uav_id;
        public string status;
        public string timestamp;
        public float overall_health;
        public bool is_anomaly;
        public float anomaly_score;
        public string active_fault;
    }

    [Serializable]
    public sealed class EngineMeasurements
    {
        public float rpm;
        public float throttle;
        public float manifold_absolute_pressure;
        public float egt;
        public float cht;
        public float intake_air_temperature;
        public float ambient_temperature;
        public float oil_pressure;
        public float oil_temperature;
        public float fuel_flow;
        public float injection_timing_deg;
        public float vibration;
        public float ambient_pressure;
        public float battery_voltage;
    }

    [Serializable]
    public sealed class HealthSnapshot
    {
        public float overall;
        public float combustion;
        public float thermal;
        public float lubrication;
        public float mechanical;
        public float electrical;
    }

    [Serializable]
    public sealed class AnomalySnapshot
    {
        public bool is_anomaly;
        public float score;
        public float confidence;
    }

    [Serializable]
    public sealed class FaultSnapshot
    {
        public string fault_type;
        public float confidence;
        public float severity;
    }

    [Serializable]
    public sealed class DegradationSnapshot
    {
        public float degradation_index;
        public float confidence;
        public string trend;
    }

    [Serializable]
    public sealed class RulSnapshot
    {
        public string status;
        public float remaining_useful_life;
        public float lower_bound;
        public float upper_bound;
        public float confidence;
    }

    [Serializable]
    public sealed class DashboardAnalytics
    {
        public AnomalySnapshot anomaly;
        public FaultSnapshot[] faults;
        public DegradationSnapshot degradation;
        public RulSnapshot rul;
    }

    [Serializable]
    public sealed class DashboardSnapshot
    {
        public string timestamp;
        public EngineMeasurements engine;
        public HealthSnapshot health;
        public DashboardAnalytics analytics;
    }

    [Serializable]
    public sealed class FaultRequest
    {
        public string fault_type;
    }

    [Serializable]
    public sealed class SimulationCommand
    {
        public float throttle;
        public string fault_type;
    }

    [Serializable]
    public sealed class SimulationStepRequest
    {
        public float dt;
        public bool auto_ingest;
    }
}