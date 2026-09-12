using AeroTwin.Core;
using AeroTwin.Networking;
using UnityEngine;

namespace AeroTwin.DigitalTwin
{
    public sealed class DigitalTwinController : MonoBehaviour
    {
        [SerializeField] private float interpolation = 6f;
        private FlightState targetFlight;
        private DashboardSnapshot dashboard;
        private AeroTwin.Aircraft.PropellerController propeller;

        public DashboardSnapshot Dashboard => dashboard;

        private void Awake()
        {
            propeller = GetComponentInChildren<AeroTwin.Aircraft.PropellerController>();
        }

        public void Synchronize(FlightState pilotState, DashboardSnapshot snapshot)
        {
            targetFlight = pilotState?.Clone();
            dashboard = snapshot;
        }

        private void Update()
        {
            if (targetFlight == null) return;
            transform.position = Vector3.Lerp(transform.position, targetFlight.position + Vector3.right * 5f, interpolation * Time.deltaTime);
            Quaternion targetRotation = Quaternion.Euler(-targetFlight.pitch, targetFlight.heading, -targetFlight.roll);
            transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, interpolation * Time.deltaTime);
            if (propeller != null) propeller.Rpm = dashboard?.engine?.rpm ?? 0f;
        }
    }
}