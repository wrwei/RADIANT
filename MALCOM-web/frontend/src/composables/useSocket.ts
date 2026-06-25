import { onMounted, onUnmounted } from "vue";
import type { ClientMessage, ServerMessage } from "../types";
import { bindSender, handleMessage, setConnected } from "../store";

// Owns the WebSocket lifecycle: connect, auto-reconnect (2s), route inbound
// messages to the store, and expose a typed sender.
export function useSocket(): void {
  let ws: WebSocket | null = null;
  let closed = false;
  let retry: ReturnType<typeof setTimeout> | null = null;

  function sendMessage(msg: ClientMessage): void {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }

  function connect(): void {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      if (!closed) retry = setTimeout(connect, 2000);
    };
    ws.onmessage = (event) => {
      try {
        handleMessage(JSON.parse(event.data) as ServerMessage);
      } catch {
        /* ignore malformed frames */
      }
    };
  }

  onMounted(() => {
    bindSender(sendMessage);
    connect();
  });

  onUnmounted(() => {
    closed = true;
    if (retry) clearTimeout(retry);
    ws?.close();
  });
}
