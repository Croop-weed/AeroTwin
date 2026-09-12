using AeroTwin.Core;
using AeroTwin.Flight;
using UnityEngine;

namespace AeroTwin.Aircraft
{
    public sealed class AircraftController : MonoBehaviour
    {
        [SerializeField] private bool acceptPlayerInput = true;
        [SerializeField] private Transform visualModel;
        [SerializeField] private PropellerController propeller;
        private IFlightDynamics dynamics;

        public FlightState State => dynamics.State;
        public bool AcceptPlayerInput { get => acceptPlayerInput; set => acceptPlayerInput = value; }

        public void Initialize(Vector3 startPosition)
        {
            dynamics = new SimpleFlightDynamics(startPosition);
            transform.position = startPosition;
        }

        private void Update()
        {
            if (dynamics == null) return;
            if (acceptPlayerInput)
            {
                float throttle = Input.GetKey(KeyCode.W) ? 100f : (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.Space) ? 5f : dynamics.State.throttle);
                float yaw = (Input.GetKey(KeyCode.D) ? 1f : 0f) - (Input.GetKey(KeyCode.A) ? 1f : 0f);
                float pitch = (Input.GetKey(KeyCode.UpArrow) ? 1f : 0f) - (Input.GetKey(KeyCode.DownArrow) ? 1f : 0f);
                float roll = (Input.GetKey(KeyCode.E) ? 1f : 0f) - (Input.GetKey(KeyCode.Q) ? 1f : 0f);
                dynamics.SetThrottle(throttle);
                dynamics.SetControlInput(yaw, pitch, roll);
                if (Input.GetKey(KeyCode.T)) dynamics.SetInjectionTiming(State.injectionTimingDeg + 10f * Time.deltaTime);
                if (Input.GetKey(KeyCode.G)) dynamics.SetInjectionTiming(State.injectionTimingDeg - 10f * Time.deltaTime);
                if (Input.GetKey(KeyCode.Y)) dynamics.SetRpmAdjustment(180f * Time.deltaTime);
                if (Input.GetKey(KeyCode.H)) dynamics.SetRpmAdjustment(-180f * Time.deltaTime);
                if (Input.GetKeyDown(KeyCode.R)) ResetAircraft();
            }

            dynamics.Step(Time.deltaTime);
            transform.position = dynamics.State.position;
            transform.rotation = Quaternion.Euler(-dynamics.State.pitch, dynamics.State.heading, -dynamics.State.roll);
            if (propeller != null) propeller.Rpm = Mathf.Lerp(900f, 3600f, dynamics.State.throttle / 100f);
        }

        public void ResetAircraft()
        {
            if (dynamics == null) return;
            dynamics.Reset();
            transform.position = dynamics.State.position;
        }
    }
}