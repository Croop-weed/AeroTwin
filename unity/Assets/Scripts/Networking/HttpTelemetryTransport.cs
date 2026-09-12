using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace AeroTwin.Networking
{
    public sealed class HttpTelemetryTransport : MonoBehaviour, ITelemetryTransport
    {
        private string baseUrl;
        private string uavId;
        private bool telemetryDiagnostics;

        public void Configure(string serverUrl, string configuredUavId, bool enableTelemetryDiagnostics = false)
        {
            baseUrl = serverUrl.TrimEnd('/');
            uavId = configuredUavId;
            telemetryDiagnostics = enableTelemetryDiagnostics;
        }

        public void SendTelemetry(TelemetryRequest telemetry, Action<TelemetryIngestResponse, string> completed)
        {
            StartCoroutine(PostJson($"/api/v1/uavs/{uavId}/telemetry", JsonUtility.ToJson(telemetry), (json, error) =>
            {
                completed?.Invoke(string.IsNullOrEmpty(error) ? JsonUtility.FromJson<TelemetryIngestResponse>(json) : null, error);
            }, telemetryDiagnostics));
        }

        public void Register(UavRegistrationRequest registration, Action<bool, string> completed)
        {
            StartCoroutine(PostJson("/api/v1/uavs", JsonUtility.ToJson(registration), (json, error) => completed?.Invoke(string.IsNullOrEmpty(error), error)));
        }

        public void SendFault(string configuredUavId, string faultType, Action<bool, string> completed)
        {
            string payload = JsonUtility.ToJson(new FaultRequest { fault_type = faultType });
            StartCoroutine(PostJson($"/api/v1/uavs/{configuredUavId}/simulation/fault", payload, (json, error) => completed?.Invoke(string.IsNullOrEmpty(error), error)));
        }

        public void StartSimulation(float throttle, Action<bool, string> completed)
        {
            StartCoroutine(PostJson($"/api/v1/uavs/{uavId}/simulation/start", JsonUtility.ToJson(new SimulationCommand { throttle = throttle }), (json, error) => completed?.Invoke(string.IsNullOrEmpty(error), error)));
        }

        public void ResetSimulation(Action<bool, string> completed)
        {
            StartCoroutine(PostJson($"/api/v1/uavs/{uavId}/simulation/reset", "{}", (json, error) => completed?.Invoke(string.IsNullOrEmpty(error), error)));
        }

        public void SetSimulationThrottle(float throttle, Action<bool, string> completed)
        {
            StartCoroutine(PostJson($"/api/v1/uavs/{uavId}/simulation/throttle", JsonUtility.ToJson(new SimulationCommand { throttle = throttle }), (json, error) => completed?.Invoke(string.IsNullOrEmpty(error), error)));
        }

        public void StepSimulation(float dt, Action<bool, string> completed)
        {
            StartCoroutine(PostJson($"/api/v1/uavs/{uavId}/simulation/step", JsonUtility.ToJson(new SimulationStepRequest { dt = dt, auto_ingest = true }), (json, error) => completed?.Invoke(string.IsNullOrEmpty(error), error)));
        }

        private IEnumerator PostJson(string path, string json, Action<string, string> completed, bool logTelemetry = false)
        {
            string url = baseUrl + path;
            using (UnityWebRequest request = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST))
            {
                byte[] body = Encoding.UTF8.GetBytes(json);
                request.uploadHandler = new UploadHandlerRaw(body);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success)
                {
                    if (logTelemetry) Debug.LogWarning($"[Telemetry] POST {url} failed -> {request.responseCode}/{request.error}");
                    completed?.Invoke(null, request.error);
                }
                else
                {
                    if (logTelemetry) Debug.Log($"[Telemetry] POST {url} -> {request.responseCode}");
                    completed?.Invoke(request.downloadHandler.text, null);
                }
            }
        }
    }
}