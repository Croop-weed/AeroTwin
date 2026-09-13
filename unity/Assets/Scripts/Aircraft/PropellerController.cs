using UnityEngine;

namespace AeroTwin.Aircraft
{
    public sealed class PropellerController : MonoBehaviour
    {
        [SerializeField] private float simulatedRpm = 2200f;
        public float Rpm { get; set; }

        private void Update()
        {
            float rpm = Rpm > 0f ? Rpm : simulatedRpm;
            transform.Rotate(Vector3.forward, rpm * 6f * Time.deltaTime, Space.Self);
        }
    }
}