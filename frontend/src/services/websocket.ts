import type { DashboardSnapshotResponse } from "../types/api";
import { API_BASE } from "./api";

export type ConnectionStatus = "CONNECTING" | "LIVE" | "DISCONNECTED";

export class TwinWebSocketClient {
  private ws: WebSocket | null = null;
  private uavId: string = "";
  private reconnectTimeout: number | null = null;
  private pingInterval: number | null = null;
  private shouldReconnect: boolean = true;
  private backoffMs: number = 1000;

  private onSnapshotCallback?: (snapshot: DashboardSnapshotResponse) => void;
  private onStatusCallback?: (status: ConnectionStatus) => void;

  constructor(
    onSnapshot?: (snapshot: DashboardSnapshotResponse) => void,
    onStatus?: (status: ConnectionStatus) => void
  ) {
    this.onSnapshotCallback = onSnapshot;
    this.onStatusCallback = onStatus;
  }

  connect(uavId: string) {
    if (this.ws && this.uavId === uavId && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.disconnect();
    this.uavId = uavId;
    this.shouldReconnect = true;
    this.initiateConnection();
  }

  private getWsUrl(uavId: string): string {
    const wsBase = API_BASE.replace(/^http/, "ws");
    return `${wsBase}/api/v1/uavs/${encodeURIComponent(uavId)}/ws`;
  }

  private initiateConnection() {
    if (!this.uavId || !this.shouldReconnect) return;

    this.onStatusCallback?.("CONNECTING");
    const url = this.getWsUrl(this.uavId);

    try {
      this.ws = new WebSocket(url);
    } catch (err) {
      console.error("[WebSocket] Failed to instantiate:", err);
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      console.log(`[WebSocket] Connected for UAV: ${this.uavId}`);
      this.backoffMs = 1000;
      this.onStatusCallback?.("LIVE");
      this.startPing();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "pong") return;
        if (data.uav && data.engine && data.health) {
          this.onSnapshotCallback?.(data as DashboardSnapshotResponse);
        }
      } catch (err) {
        console.warn("[WebSocket] Error parsing message:", err);
      }
    };

    this.ws.onerror = (event) => {
      console.warn("[WebSocket] Error occurred:", event);
    };

    this.ws.onclose = (event) => {
      console.log(`[WebSocket] Connection closed (code: ${event.code})`);
      this.stopPing();
      this.onStatusCallback?.("DISCONNECTED");
      if (this.shouldReconnect) {
        this.scheduleReconnect();
      }
    };
  }

  private startPing() {
    this.stopPing();
    this.pingInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send("ping");
      }
    }, 15000);
  }

  private stopPing() {
    if (this.pingInterval !== null) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout !== null) {
      clearTimeout(this.reconnectTimeout);
    }
    this.reconnectTimeout = window.setTimeout(() => {
      this.backoffMs = Math.min(this.backoffMs * 1.5, 6000);
      this.initiateConnection();
    }, this.backoffMs);
  }

  disconnect() {
    this.shouldReconnect = false;
    this.stopPing();
    if (this.reconnectTimeout !== null) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      this.ws.onopen = null;
      this.ws.close();
      this.ws = null;
    }
    this.onStatusCallback?.("DISCONNECTED");
  }
}
