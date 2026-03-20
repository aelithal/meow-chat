const API_BASE = 'http://localhost:8000';

const api = {
  async _request(method, path, body = null, token = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(API_BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const msg = data.detail
        ? (Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail)
        : 'Ошибка сервера';
      const err = new Error(msg);
      err.status = res.status;
      throw err;
    }
    return data;
  },

  register: (username, password) =>
    api._request('POST', '/auth/register', { username, password }),

  login: (username, password) =>
    api._request('POST', '/auth/login', { username, password }),

  me: (token) =>
    api._request('GET', '/auth/me', null, token),

  getRooms: (token) =>
    api._request('GET', '/rooms', null, token),

  createRoom: (token, name) =>
    api._request('POST', '/rooms', { name }, token),

  getHistory: (token, roomId, limit = 50) =>
    api._request('GET', `/rooms/${roomId}/messages?limit=${limit}`, null, token),

  deleteRoom: (token, roomId) =>
    api._request('DELETE', `/rooms/${roomId}`, null, token),
};

function showAlert(el, message, type = 'error') {
  el.textContent = message;
  el.className = `alert alert-${type} show`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
