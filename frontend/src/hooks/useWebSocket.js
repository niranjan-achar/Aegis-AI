import { useEffect, useRef, useState } from "react";

export function useWebSocket(url, enabled = true) {
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState(enabled ? "connecting" : "idle");
  const reconnectRef = useRef(0);
  const socketRef = useRef(null);

  useEffect(() => {
    if (!enabled) {
      setStatus("idle");
      return undefined;
    }

    let cancelled = false;

    const connect = () => {
      setStatus("connecting");
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        reconnectRef.current = 0;
        if (!cancelled) {
          setStatus("open");
        }
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setMessages((current) => [...current.slice(-99), parsed]);
        } catch {
          setMessages((current) => [...current.slice(-99), { event: "raw", data: event.data }]);
        }
      };

      socket.onerror = () => {
        if (!cancelled) {
          setStatus("error");
        }
      };

      socket.onclose = () => {
        if (cancelled) {
          return;
        }
        setStatus("reconnecting");
        const delay = Math.min(1000 * 2 ** reconnectRef.current, 8000);
        reconnectRef.current += 1;
        window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      socketRef.current?.close();
    };
  }, [enabled, url]);

  return { messages, status };
}
