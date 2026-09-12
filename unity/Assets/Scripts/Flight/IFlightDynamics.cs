using AeroTwin.Core;

namespace AeroTwin.Flight
{
    public interface IFlightDynamics
    {
        FlightState State { get; }
        void Reset();
        void SetThrottle(float target);
        void SetRpmAdjustment(float adjustment);
        void SetInjectionTiming(float target);
        void SetControlInput(float yaw, float pitch, float roll);
        void Step(float deltaTime);
    }
}