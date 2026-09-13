using System;
using UnityEngine;

namespace AeroTwin.Core
{
    [Serializable]
    public class FlightState
    {
        public string timestamp;
        public Vector3 position;
        public Vector3 velocity;
        public float speed;
        public float altitude;
        public float verticalSpeed;
        public float heading;
        public float pitch;
        public float roll;
        public float yaw;
        public float throttle;
        public float targetRpm;
        public float rpm;
        public float manifoldAbsolutePressure;
        public float egt;
        public float cht;
        public float oilPressure;
        public float oilTemperature;
        public float fuelFlow;
        public float vibration;
        public float batteryVoltage;
        public float injectionTimingDeg;

        public FlightState Clone()
        {
            return new FlightState
            {
                timestamp = timestamp,
                position = position,
                velocity = velocity,
                speed = speed,
                altitude = altitude,
                verticalSpeed = verticalSpeed,
                heading = heading,
                pitch = pitch,
                roll = roll,
                yaw = yaw,
                throttle = throttle,
                targetRpm = targetRpm,
                rpm = rpm,
                manifoldAbsolutePressure = manifoldAbsolutePressure,
                egt = egt,
                cht = cht,
                oilPressure = oilPressure,
                oilTemperature = oilTemperature,
                fuelFlow = fuelFlow,
                vibration = vibration,
                batteryVoltage = batteryVoltage,
                injectionTimingDeg = injectionTimingDeg
            };
        }
    }
}