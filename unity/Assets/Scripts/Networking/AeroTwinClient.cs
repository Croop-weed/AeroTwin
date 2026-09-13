using System;
using AeroTwin.Aircraft;
using AeroTwin.Core;
using UnityEngine;

namespace AeroTwin.Networking
{
    public sealed class AeroTwinClient : MonoBehaviour
    {
        [Header("Connection")]
        public ConnectionMode mode = ConnectionMode.Mock;
        public string serverUrl = "http://127.0.0.1:8000";
        public string uavId = "UAV-001";
        public string engineId = "ENG-UAV-001";
        public string modelType = "piston";
        [Range(1f, 30f)] public float sendRateHz = 10f;
        public bool telemetryDiagnostics = true;

        private AircraftController pilot;
        private HttpTelemetryTransport http;
        private RealtimeWebSocketTransport realtime;
        private float sendTimer;
        private bool registered;
        private string mockFault = "NONE";
        private bool backendFaultActive;

        public DashboardSnapshot CurrentDashboard { get; private set; }
        public TelemetryRequest LastPublishedTelemetry { get; private set; }
        public string LastError { get; private set; }
        public event Action<DashboardSnapshot> DashboardUpdated;

        public void Initialize(AircraftController pilotAircraft)
        {
            pilot = pilotAircraft;
            Debug.Log($"[AeroTwin] Initialize mode={mode} server={serverUrl} uav={uavId} engine={engineId} sendRateHz={sendRateHz}");
            http = gameObject.AddComponent<HttpTelemetryTransport>();
            http.Configure(serverUrl, uavId, telemetryDiagnostics);
            realtime = gameObject.AddComponent<RealtimeWebSocketTransport>();
            realtime.SnapshotReceived += OnDashboardSnapshot;

            if (mode == ConnectionMode.Live)
            {
                UavRegistrationRequest registration = new UavRegistrationRequest
                {
                    uav_id = uavId,
                    engine_id = engineId,
                    model_type = modelType,
                    configuration = new RegistrationMap(),
                    metadata = new RegistrationMap()
                };
                http.Register(registration, (success, error) =>
                {
                    registered = success || error != null && error.Contains("409");
                    LastError = success ? null : error;
                    if (registered)
                    {
                        Debug.Log($"[AeroTwin] UAV registration ready: {uavId}/{engineId}");
                    }
                    else
                    {
                        Debug.LogError($"[AeroTwin] UAV registration failed: {error}");
                    }
                    if (registered) realtime.Connect(serverUrl, uavId);
                });
            }
            else
            {
                registered = true;
                CurrentDashboard = CreateMockSnapshot();
            }
        }

        private void Update()
        {
            if (pilot == null || !registered) return;
            sendTimer += Time.deltaTime;
            if (sendTimer < 1f / Mathf.Max(1f, sendRateHz)) return;
            sendTimer = 0f;
            TelemetryRequest telemetry = BuildTelemetry(pilot.State);
            LastPublishedTelemetry = telemetry;
            if (mode == ConnectionMode.Live && backendFaultActive)
            {
                http.SetSimulationThrottle(pilot.State.throttle, (success, error) =>
                {
                    if (!success) { LastError = error; return; }
                    http.StepSimulation(1f / Mathf.Max(1f, sendRateHz), OnSimulationCommandResponse);
                });
            }
            else if (mode == ConnectionMode.Live) http.SendTelemetry(telemetry, OnTelemetryResponse);
            if (mode != ConnectionMode.Live) OnDashboardSnapshot(CreateMockSnapshot(telemetry));
        }

        private TelemetryRequest BuildTelemetry(FlightState state)
        {
            return new TelemetryRequest
            {
                timestamp = state.timestamp,
                rpm = state.rpm,
                throttle = state.throttle,
                manifold_absolute_pressure = state.manifoldAbsolutePressure,
                egt = state.egt,
                cht = state.cht,
                intake_air_temperature = 25f,
                ambient_temperature = 22f,
                oil_pressure = state.oilPressure,
                oil_temperature = state.oilTemperature,
                fuel_flow = state.fuelFlow,
                injection_timing_deg = state.injectionTimingDeg,
                vibration = state.vibration,
                ambient_pressure = 101.3f,
                battery_voltage = state.batteryVoltage
            };
        }

        private DashboardSnapshot CreateMockSnapshot(TelemetryRequest telemetry = null)
        {
            telemetry ??= BuildTelemetry(pilot.State);
            bool faultActive = mockFault != "NONE";
            float health = Mathf.Clamp(100f - Mathf.Max(0f, telemetry.egt - 690f) * 0.12f - telemetry.vibration * 2f - (faultActive ? 18f : 0f), 0f, 100f);
            return new DashboardSnapshot
            {
                timestamp = telemetry.timestamp,
                engine = new EngineMeasurements
                {
                    rpm = telemetry.rpm, throttle = telemetry.throttle, manifold_absolute_pressure = telemetry.manifold_absolute_pressure,
                    egt = telemetry.egt, cht = telemetry.cht, intake_air_temperature = telemetry.intake_air_temperature,
                    ambient_temperature = telemetry.ambient_temperature, oil_pressure = telemetry.oil_pressure,
                    oil_temperature = telemetry.oil_temperature, fuel_flow = telemetry.fuel_flow,
                    injection_timing_deg = telemetry.injection_timing_deg, vibration = telemetry.vibration,
                    ambient_pressure = telemetry.ambient_pressure, battery_voltage = telemetry.battery_voltage
                },
                health = new HealthSnapshot { overall = health, combustion = health + 2f, thermal = health - 3f, lubrication = health + 1f, mechanical = health, electrical = 99f },
                analytics = new DashboardAnalytics
                {
                    anomaly = new AnomalySnapshot { is_anomaly = health < 75f, score = 1f - health / 100f, confidence = 1f },
                    faults = faultActive ? new[] { new FaultSnapshot { fault_type = mockFault, confidence = 0.87f, severity = 0.7f } } : new FaultSnapshot[0],
                    degradation = new DegradationSnapshot { degradation_index = 1f - health / 100f, confidence = 1f, trend = health > 90f ? "STABLE" : "WORSENING" },
                    rul = new RulSnapshot { status = "N/A", confidence = 0f }
                }
            };
        }

        private void OnTelemetryResponse(TelemetryIngestResponse response, string error)
        {
            LastError = string.IsNullOrEmpty(error) ? null : error;
            if (!telemetryDiagnostics || LastPublishedTelemetry == null) return;
            if (response != null)
            {
                Debug.Log($"[Telemetry] RPM={LastPublishedTelemetry.rpm:0.0}, Throttle={LastPublishedTelemetry.throttle:0.0}, MAP={LastPublishedTelemetry.manifold_absolute_pressure:0.0}, EGT={LastPublishedTelemetry.egt:0.0}, CHT={LastPublishedTelemetry.cht:0.0} Response=200");
            }
            else
            {
                Debug.LogWarning($"[Telemetry] RPM={LastPublishedTelemetry.rpm:0.0}, Throttle={LastPublishedTelemetry.throttle:0.0}, MAP={LastPublishedTelemetry.manifold_absolute_pressure:0.0}, EGT={LastPublishedTelemetry.egt:0.0}, CHT={LastPublishedTelemetry.cht:0.0} POST failed -> {error}");
            }
        }

        private void OnDashboardSnapshot(DashboardSnapshot snapshot)
        {
            if (snapshot == null) return;
            CurrentDashboard = snapshot;
            DashboardUpdated?.Invoke(snapshot);
        }

        public void InjectFault(string faultType)
        {
            if (mode == ConnectionMode.Live)
            {
                if (faultType == "NONE")
                {
                    http.SendFault(uavId, faultType, (success, error) =>
                    {
                        backendFaultActive = false;
                        LastError = success ? null : error;
                    });
                }
                else
                {
                    http.StartSimulation(pilot.State.throttle, (started, startError) =>
                    {
                        if (!started) { LastError = startError; return; }
                        http.SendFault(uavId, faultType, (success, error) =>
                        {
                            backendFaultActive = success;
                            LastError = success ? null : error;
                        });
                    });
                }
            }
            else if (mode == ConnectionMode.Mock) { mockFault = faultType; CurrentDashboard = CreateMockSnapshot(); }
        }

        public void StartBackendSimulation()
        {
            if (mode == ConnectionMode.Live) http.StartSimulation(pilot.State.throttle, (success, error) => LastError = success ? null : error);
        }

        public void ResetBackendSimulation()
        {
            if (mode == ConnectionMode.Live) http.ResetSimulation((success, error) =>
            {
                backendFaultActive = false;
                LastError = success ? null : error;
            });
        }

        public void SetMode(ConnectionMode newMode)
        {
            mode = newMode;
            realtime.Disconnect();
            backendFaultActive = false;
            LastError = null;
            if (mode == ConnectionMode.Live)
            {
                http.Register(new UavRegistrationRequest
                {
                    uav_id = uavId,
                    engine_id = engineId,
                    model_type = modelType,
                    configuration = new RegistrationMap(),
                    metadata = new RegistrationMap()
                }, (success, error) =>
                {
                    registered = success || (error != null && error.Contains("409"));
                    LastError = success ? null : error;
                    if (registered) realtime.Connect(serverUrl, uavId);
                });
            }
            else
            {
                registered = true;
                if (mode == ConnectionMode.Mock) CurrentDashboard = CreateMockSnapshot();
            }
        }

        private void OnSimulationCommandResponse(bool success, string error)
        {
            if (!success) LastError = error;
        }
    }
}