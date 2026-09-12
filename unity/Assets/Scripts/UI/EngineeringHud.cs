using AeroTwin.Aircraft;
using AeroTwin.Core;
using AeroTwin.Networking;
using UnityEngine;

namespace AeroTwin.UI
{
    public sealed class EngineeringHud : MonoBehaviour
    {
        private AircraftController pilot;
        private AeroTwinClient client;
        private bool paused;
        private GUIStyle heading;
        private GUIStyle value;
        private GUIStyle alert;

        public void Initialize(AircraftController aircraft, AeroTwinClient twinClient)
        {
            pilot = aircraft;
            client = twinClient;
        }

        private void OnGUI()
        {
            if (pilot == null || client == null) return;
            EnsureStyles();
            DashboardSnapshot snapshot = client.CurrentDashboard;
            EngineMeasurements engine = snapshot?.engine;
            HealthSnapshot health = snapshot?.health;
            DashboardAnalytics analytics = snapshot?.analytics;

            GUILayout.BeginArea(new Rect(18f, 18f, 390f, Screen.height - 36f), GUI.skin.box);
            GUILayout.Label("AEROTWIN // UAV SIMULATOR", heading);
            GUILayout.Label("PILOT / SIMULATOR", heading);
            Row("Speed", pilot.State.speed.ToString("0.0") + " m/s");
            Row("Altitude", pilot.State.altitude.ToString("0") + " m");
            Row("Heading", pilot.State.heading.ToString("0") + " deg");
            Row("Vertical speed", pilot.State.verticalSpeed.ToString("+0.0;-0.0;0.0") + " m/s");
            Row("Throttle", pilot.State.throttle.ToString("0") + "%");

            GUILayout.Space(10f);
            GUILayout.Label("DIGITAL TWIN // BACKEND STATE", heading);
            Row("RPM", Number(engine?.rpm, "0"));
            Row("Throttle", Number(engine?.throttle, "0") + "%");
            Row("MAP", Number(engine?.manifold_absolute_pressure, "0.0") + " kPa");
            Row("EGT / CHT", Number(engine?.egt, "0") + " / " + Number(engine?.cht, "0") + " C");
            Row("Oil pressure", Number(engine?.oil_pressure, "0.0") + " psi");
            Row("Oil temperature", Number(engine?.oil_temperature, "0") + " C");
            Row("Fuel flow", Number(engine?.fuel_flow, "0.0") + " L/h");
            Row("Vibration", Number(engine?.vibration, "0.00") + " mm/s");
            Row("Battery", Number(engine?.battery_voltage, "0.0") + " V");
            Row("Injection timing", Number(engine?.injection_timing_deg, "0.0") + " deg");

            GUILayout.Space(10f);
            GUILayout.Label("ENGINE CONTROLS", heading);
            Row("Throttle", pilot.State.throttle.ToString("0") + "%  [W / S]");
            Row("Target RPM", pilot.State.targetRpm.ToString("0") + "  [Y / H]");
            Row("Injection timing", pilot.State.injectionTimingDeg.ToString("0.0") + " deg  [T / G]");
            GUILayout.Label("Controls are applied to PilotUAV, then published as telemetry.", value);

            GUILayout.Space(10f);
            GUILayout.Label("HEALTH", heading);
            Row("Overall", Number(health?.overall, "0.0") + "%");
            Row("Combustion", Number(health?.combustion, "0.0") + "%");
            Row("Thermal", Number(health?.thermal, "0.0") + "%");
            Row("Lubrication", Number(health?.lubrication, "0.0") + "%");
            Row("Mechanical", Number(health?.mechanical, "0.0") + "%");
            Row("Electrical", Number(health?.electrical, "0.0") + "%");

            GUILayout.Space(10f);
            GUILayout.Label("ANALYTICS", heading);
            Row("Anomaly", analytics?.anomaly != null && analytics.anomaly.is_anomaly ? "ABNORMAL" : "NORMAL");
            Row("Score", Number(analytics?.anomaly?.score, "0.00"));
            Row("Degradation", analytics?.degradation?.trend ?? "N/A");
            Row("RUL", analytics?.rul == null || analytics.rul.status != "AVAILABLE" ? "N/A" : analytics.rul.remaining_useful_life.ToString("0.0"));
            if (analytics?.faults != null && analytics.faults.Length > 0)
            {
                GUILayout.Label("ENGINE FAULT // " + analytics.faults[0].fault_type, alert);
                Row("Confidence", (analytics.faults[0].confidence * 100f).ToString("0") + "%");
            }

            GUILayout.Space(12f);
            GUILayout.BeginHorizontal();
            if (GUILayout.Button(paused ? "RESUME" : "PAUSE")) { paused = !paused; Time.timeScale = paused ? 0f : 1f; }
            if (GUILayout.Button("RESET")) { pilot.ResetAircraft(); client.ResetBackendSimulation(); }
            if (GUILayout.Button("START")) client.StartBackendSimulation();
            GUILayout.EndHorizontal();
            GUILayout.Label("MODE: " + client.mode.ToString().ToUpperInvariant() + "   UAV: " + client.uavId, value);
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("OFFLINE")) client.SetMode(ConnectionMode.Offline);
            if (GUILayout.Button("MOCK")) client.SetMode(ConnectionMode.Mock);
            if (GUILayout.Button("LIVE")) client.SetMode(ConnectionMode.Live);
            GUILayout.EndHorizontal();
            GUILayout.Label("A/D heading   arrows pitch   Q/E roll   R reset", value);
            if (!string.IsNullOrEmpty(client.LastError)) GUILayout.Label("LINK: " + client.LastError, alert);
            GUILayout.EndArea();

            GUILayout.BeginArea(new Rect(Screen.width - 290f, 18f, 272f, 330f), GUI.skin.box);
            GUILayout.Label("FAULT INJECTION", heading);
            FaultButton("OVERHEATING");
            FaultButton("LUBRICATION_FAILURE");
            FaultButton("INJECTOR_DEGRADATION");
            FaultButton("MISFIRE");
            FaultButton("COMBUSTION_INSTABILITY");
            FaultButton("ABNORMAL_VIBRATION");
            FaultButton("SENSOR_DRIFT");
            FaultButton("SENSOR_FAILURE");
            FaultButton("CLEAR", "NONE");
            GUILayout.EndArea();
        }

        private void FaultButton(string label, string valueOverride = null)
        {
            if (GUILayout.Button(label)) client.InjectFault(valueOverride ?? label);
        }

        private void Row(string label, string text)
        {
            GUILayout.BeginHorizontal();
            GUILayout.Label(label, value, GUILayout.Width(155f));
            GUILayout.Label(text, value);
            GUILayout.EndHorizontal();
        }

        private static string Number(float? number, string format) => number.HasValue ? number.Value.ToString(format) : "--";

        private void EnsureStyles()
        {
            if (heading != null) return;
            heading = new GUIStyle(GUI.skin.label) { fontSize = 15, fontStyle = FontStyle.Bold, normal = { textColor = new Color(0.25f, 0.85f, 1f) } };
            value = new GUIStyle(GUI.skin.label) { fontSize = 13, normal = { textColor = new Color(0.85f, 0.9f, 0.92f) } };
            alert = new GUIStyle(value) { fontStyle = FontStyle.Bold, normal = { textColor = new Color(1f, 0.35f, 0.22f) } };
        }
    }
}