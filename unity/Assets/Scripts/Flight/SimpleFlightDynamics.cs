using System;
using AeroTwin.Core;
using UnityEngine;

namespace AeroTwin.Flight
{
    public sealed class SimpleFlightDynamics : IFlightDynamics
    {
        private readonly FlightState state = new FlightState();
        private float targetThrottle;
        private float targetYaw;
        private float targetPitch;
        private float targetRoll;
        private float targetRpmOffset;
        private float targetInjectionTiming;
        private readonly Vector3 startPosition;

        public FlightState State => state;

        public SimpleFlightDynamics(Vector3 startPosition)
        {
            this.startPosition = startPosition;
            state.position = startPosition;
            state.altitude = startPosition.y;
            Reset();
        }

        public void Reset()
        {
            state.position = startPosition;
            state.timestamp = DateTime.UtcNow.ToString("O");
            state.velocity = Vector3.forward * 28f;
            state.speed = 28f;
            state.altitude = state.position.y;
            state.verticalSpeed = 0f;
            state.heading = 0f;
            state.pitch = 0f;
            state.roll = 0f;
            state.yaw = 0f;
            state.throttle = 35f;
            state.targetRpm = 1900f;
            state.rpm = 1900f;
            state.manifoldAbsolutePressure = 63f;
            state.egt = 590f;
            state.cht = 145f;
            state.oilPressure = 42f;
            state.oilTemperature = 82f;
            state.fuelFlow = 13f;
            state.vibration = 0.95f;
            state.batteryVoltage = 13.35f;
            state.injectionTimingDeg = 12f;
            targetThrottle = 35f;
            targetYaw = targetPitch = targetRoll = 0f;
            targetRpmOffset = 0f;
            targetInjectionTiming = 12f;
        }

        public void SetThrottle(float target) => targetThrottle = Mathf.Clamp(target, 0f, 100f);

        public void SetRpmAdjustment(float adjustment)
        {
            targetRpmOffset = Mathf.Clamp(targetRpmOffset + adjustment, -600f, 600f);
        }

        public void SetInjectionTiming(float target)
        {
            targetInjectionTiming = Mathf.Clamp(target, 0f, 30f);
        }

        public void SetControlInput(float yaw, float pitch, float roll)
        {
            targetYaw = Mathf.Clamp(yaw, -1f, 1f);
            targetPitch = Mathf.Clamp(pitch, -1f, 1f);
            targetRoll = Mathf.Clamp(roll, -1f, 1f);
        }

        public void Step(float deltaTime)
        {
            float dt = Mathf.Max(deltaTime, 0.001f);
            state.throttle = Mathf.MoveTowards(state.throttle, targetThrottle, 35f * dt);
            state.injectionTimingDeg = Mathf.MoveTowards(state.injectionTimingDeg, targetInjectionTiming, 8f * dt);
            float timingEfficiency = Mathf.Clamp01(1f - Mathf.Abs(state.injectionTimingDeg - 12f) / 18f);
            float throttleRatio = state.throttle / 100f;
            float governorRpm = Mathf.Lerp(900f, 3600f, throttleRatio) + targetRpmOffset;
            state.targetRpm = Mathf.Clamp(governorRpm * Mathf.Lerp(0.88f, 1f, timingEfficiency), 750f, 3900f);
            state.rpm = Mathf.MoveTowards(state.rpm, state.targetRpm, 900f * dt);
            float rpmRatio = state.rpm / 3600f;
            float load = Mathf.Clamp01(throttleRatio * 0.7f + rpmRatio * 0.3f);
            float targetMap = 42f + throttleRatio * 58f;
            float targetEgt = 500f + load * 235f + (1f - timingEfficiency) * 35f;
            float targetCht = 105f + load * 88f + (1f - timingEfficiency) * 12f;
            float targetOilTemperature = 70f + load * 38f;
            float targetOilPressure = 18f + rpmRatio * 42f;
            float targetFuelFlow = throttleRatio * 26f + rpmRatio * 14f;
            float targetVibration = 0.35f + rpmRatio * 0.7f + load * 0.8f + (1f - timingEfficiency) * 0.45f;
            float targetBattery = 12.45f + Mathf.Clamp01(rpmRatio) * 1.35f;
            state.manifoldAbsolutePressure = Mathf.Lerp(state.manifoldAbsolutePressure, targetMap, 3.5f * dt);
            state.egt = Mathf.Lerp(state.egt, targetEgt, 1.8f * dt);
            state.cht = Mathf.Lerp(state.cht, targetCht, 0.65f * dt);
            state.oilTemperature = Mathf.Lerp(state.oilTemperature, targetOilTemperature, 0.8f * dt);
            state.oilPressure = Mathf.Lerp(state.oilPressure, targetOilPressure, 3f * dt);
            state.fuelFlow = Mathf.Lerp(state.fuelFlow, targetFuelFlow, 4f * dt);
            state.vibration = Mathf.Lerp(state.vibration, targetVibration, 3f * dt);
            state.batteryVoltage = Mathf.Lerp(state.batteryVoltage, targetBattery, 2f * dt);
            state.speed = Mathf.MoveTowards(state.speed, Mathf.Lerp(18f, 78f, state.throttle / 100f), 18f * dt);
            state.heading = Mathf.Repeat(state.heading + targetYaw * 38f * dt + 360f, 360f);
            state.pitch = Mathf.MoveTowards(state.pitch, targetPitch * 18f, 24f * dt);
            state.roll = Mathf.MoveTowards(state.roll, targetRoll * 32f, 48f * dt);
            state.yaw = state.heading;

            float headingRadians = state.heading * Mathf.Deg2Rad;
            float climb = Mathf.Sin(state.pitch * Mathf.Deg2Rad) * state.speed;
            state.verticalSpeed = climb;
            state.altitude = Mathf.Max(5f, state.altitude + climb * dt);
            Vector3 direction = new Vector3(Mathf.Sin(headingRadians), climb / Mathf.Max(state.speed, 1f), Mathf.Cos(headingRadians)).normalized;
            state.velocity = direction * state.speed;
            state.position += state.velocity * dt;
            state.position.y = state.altitude;
            state.timestamp = DateTime.UtcNow.ToString("O");
        }
    }
}