using System;

namespace AeroTwin.Networking
{
    public interface ITelemetryTransport
    {
        void SendTelemetry(TelemetryRequest telemetry, Action<TelemetryIngestResponse, string> completed);
        void Register(UavRegistrationRequest registration, Action<bool, string> completed);
        void SendFault(string uavId, string faultType, Action<bool, string> completed);
    }
}