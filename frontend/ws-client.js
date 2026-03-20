const WS_BASE = 'ws://localhost:8000';

function createWsClient({ token, roomId, onMessage, onOpen, onClose }) {
  let ws         = null;
  let closed     = false;
  let retryDelay = 1500;
  const MAX_DELAY = 15000;

  function connect() {
    if (closed) return;
    const url = `${WS_BASE}/ws/${roomId}?token=${encodeURIComponent(token)}`;
    ws = new WebSocket(url);

    ws.onopen = () => { retryDelay = 1500; onOpen?.(); };

    ws.onmessage = (event) => {
      try { onMessage(JSON.parse(event.data)); }
      catch { console.warn('WS: ошибка парсинга', event.data); }
    };

    ws.onclose = (event) => {
      if (closed) return;
      onClose?.();
      if (event.code === 4001 || event.code === 4004) { closed = true; return; }
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 1.5, MAX_DELAY);
    };

    ws.onerror = () => {};
  }

  connect();

  return {
    send(data) {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
    },
    close() { closed = true; ws?.close(); },
  };
}

function createGlobalWsClient({ token, onMessage }) {
  let ws         = null;
  let closed     = false;
  let retryDelay = 2000;
  const MAX_DELAY = 30000;

  function connect() {
    if (!token || token === 'null') return { close() {} };
    if (closed) return;
    const url = `${WS_BASE}/ws/global?token=${encodeURIComponent(token)}`;
    ws = new WebSocket(url);

    ws.onopen = () => { retryDelay = 2000; };

    ws.onmessage = (event) => {
      try { onMessage(JSON.parse(event.data)); }
      catch {}
    };

    ws.onclose = (event) => {
      if (closed) return;
      if (event.code === 4001) { closed = true; return; }
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 1.5, MAX_DELAY);
    };

    ws.onerror = () => {};
  }

  connect();

  return {
    close() { closed = true; ws?.close(); },
  };
}
