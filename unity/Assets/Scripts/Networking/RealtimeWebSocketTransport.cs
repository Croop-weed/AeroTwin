using System;
using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace AeroTwin.Networking
{
    public sealed class RealtimeWebSocketTransport : MonoBehaviour
    {
        private readonly ConcurrentQueue<string> pendingSnapshots = new ConcurrentQueue<string>();
        private ClientWebSocket socket;
        private CancellationTokenSource cancellation;

        public event Action<DashboardSnapshot> SnapshotReceived;
        public bool IsConnected => socket != null && socket.State == WebSocketState.Open;

        public void Connect(string serverUrl, string uavId)
        {
            Disconnect();
            socket = new ClientWebSocket();
            cancellation = new CancellationTokenSource();
            string wsUrl = serverUrl.Replace("https://", "wss://").Replace("http://", "ws://").TrimEnd('/') + "/api/v1/uavs/" + uavId + "/ws";
            _ = ReceiveLoop(wsUrl, cancellation.Token);
        }

        private async Task ReceiveLoop(string url, CancellationToken token)
        {
            try
            {
                await socket.ConnectAsync(new Uri(url), token);
                Debug.Log("[WebSocket] Connected: " + url);
                byte[] buffer = new byte[16384];
                while (socket.State == WebSocketState.Open && !token.IsCancellationRequested)
                {
                    WebSocketReceiveResult result = await socket.ReceiveAsync(new ArraySegment<byte>(buffer), token);
                    if (result.MessageType == WebSocketMessageType.Close) break;
                    pendingSnapshots.Enqueue(Encoding.UTF8.GetString(buffer, 0, result.Count));
                }
            }
            catch (Exception exception)
            {
                Debug.LogWarning("AeroTwin WebSocket unavailable: " + exception.Message);
            }
        }

        private void Update()
        {
            while (pendingSnapshots.TryDequeue(out string json))
            {
                try
                {
                    DashboardSnapshot snapshot = JsonUtility.FromJson<DashboardSnapshot>(json);
                    Debug.Log($"[WebSocket] DashboardSnapshot received: RPM={snapshot?.engine?.rpm:0.0}, Health={snapshot?.health?.overall:0.0}, Faults={snapshot?.analytics?.faults?.Length ?? 0}");
                    SnapshotReceived?.Invoke(snapshot);
                }
                catch (Exception exception) { Debug.LogWarning("Invalid dashboard snapshot: " + exception.Message); }
            }
        }

        public void SendPing()
        {
            if (IsConnected) _ = socket.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes("ping")), WebSocketMessageType.Text, true, cancellation.Token);
        }

        public void Disconnect()
        {
            cancellation?.Cancel();
            socket?.Dispose();
            socket = null;
        }

        private void OnDestroy() => Disconnect();
    }
}