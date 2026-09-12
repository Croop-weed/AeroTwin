using UnityEngine;

namespace AeroTwin.CameraSystem
{
    public sealed class ChaseCamera : MonoBehaviour
    {
        public Transform target;
        public Vector3 offset = new Vector3(0f, 8f, -18f);
        public float followSpeed = 5f;

        private void LateUpdate()
        {
            if (target == null) return;
            Vector3 desired = target.TransformPoint(offset);
            transform.position = Vector3.Lerp(transform.position, desired, followSpeed * Time.deltaTime);
            transform.LookAt(target.position + Vector3.up * 1.5f);
        }
    }
}