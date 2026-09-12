using AeroTwin.Aircraft;
using AeroTwin.CameraSystem;
using AeroTwin.DigitalTwin;
using AeroTwin.Networking;
using AeroTwin.UI;
using UnityEngine;

namespace AeroTwin.Core
{
    public sealed class AeroTwinBootstrap : MonoBehaviour
    {
        public ConnectionMode connectionMode = ConnectionMode.Live;
        public bool digitalTwinOnly;
        public string serverUrl = "http://127.0.0.1:8000";
        public string uavId = "UAV-001";

        private AircraftController pilot;
        private DigitalTwinController digitalTwin;
        private AeroTwinClient client;

        private void Awake()
        {
            Application.targetFrameRate = 60;
            CreateEnvironment();
            pilot = CreateAircraft("PilotUAV", new Vector3(0f, 80f, 0f), true, true, new Color(1f, 0.55f, 0.12f)).GetComponent<AircraftController>();
            GameObject twinObject = CreateAircraft("DigitalTwinUAV", new Vector3(5f, 80f, 0f), false, false, new Color(0.12f, 0.75f, 1f));
            digitalTwin = twinObject.AddComponent<DigitalTwinController>();
            client = gameObject.AddComponent<AeroTwinClient>();
            client.mode = connectionMode;
            client.serverUrl = serverUrl;
            client.uavId = uavId;
            client.Initialize(pilot);
            EngineeringHud hud = gameObject.AddComponent<EngineeringHud>();
            hud.Initialize(pilot, client);
            SetupCamera(twinObject.transform);
        }

        private void Update()
        {
            if (digitalTwin != null && client != null) digitalTwin.Synchronize(pilot.State, client.CurrentDashboard);
        }

        private GameObject CreateAircraft(string objectName, Vector3 position, bool acceptsInput, bool withFlightDynamics, Color modelColor)
        {
            GameObject root = new GameObject(objectName);
            root.transform.position = position;
            AircraftController controller = null;
            if (withFlightDynamics)
            {
                controller = root.AddComponent<AircraftController>();
                controller.AcceptPlayerInput = acceptsInput;
                controller.Initialize(position);
            }

            GameObject visual = new GameObject("VisualModel");
            visual.transform.SetParent(root.transform, false);
            CreatePrimitive(PrimitiveType.Cube, "Fuselage", visual.transform, new Vector3(0f, 0f, 0.2f), new Vector3(1.4f, 0.55f, 5.2f), modelColor);
            CreatePrimitive(PrimitiveType.Cube, "MainWing", visual.transform, new Vector3(0f, 0f, 0.25f), new Vector3(9f, 0.18f, 1.2f), modelColor);
            CreatePrimitive(PrimitiveType.Cube, "Tailplane", visual.transform, new Vector3(0f, 0.28f, -2f), new Vector3(3.1f, 0.12f, 0.8f), modelColor);
            CreatePrimitive(PrimitiveType.Cube, "VerticalTail", visual.transform, new Vector3(0f, 0.75f, -1.8f), new Vector3(0.12f, 1.2f, 0.85f), modelColor);
            GameObject propeller = CreatePrimitive(PrimitiveType.Cube, "Propeller", visual.transform, new Vector3(0f, 0f, 2.85f), new Vector3(3.4f, 0.08f, 0.12f), modelColor);
            propeller.AddComponent<PropellerController>();
            return root;
        }

        private static GameObject CreatePrimitive(PrimitiveType type, string objectName, Transform parent, Vector3 localPosition, Vector3 scale, Color color)
        {
            GameObject item = GameObject.CreatePrimitive(type);
            item.name = objectName;
            item.transform.SetParent(parent, false);
            item.transform.localPosition = localPosition;
            item.transform.localScale = scale;
            item.GetComponent<Renderer>().material.color = color;
            return item;
        }

        private static void CreateEnvironment()
        {
            GameObject ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.name = "Ground";
            ground.transform.localScale = new Vector3(80f, 1f, 80f);
            ground.GetComponent<Renderer>().material.color = new Color(0.08f, 0.13f, 0.14f);
            GameObject lightObject = new GameObject("Sun");
            Light light = lightObject.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.2f;
            lightObject.transform.rotation = Quaternion.Euler(45f, -30f, 0f);
            RenderSettings.ambientLight = new Color(0.18f, 0.23f, 0.28f);
        }

        private void SetupCamera(Transform target)
        {
            GameObject cameraObject = new GameObject("ChaseCamera");
            Camera camera = cameraObject.AddComponent<Camera>();
            camera.fieldOfView = 62f;
            ChaseCamera chase = cameraObject.AddComponent<ChaseCamera>();
            chase.target = target;
            cameraObject.transform.position = target.position + chase.offset;
        }
    }
}