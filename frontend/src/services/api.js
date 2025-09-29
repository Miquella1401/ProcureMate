import axios from 'axios';

// Base URL from .env (VITE_API_URL) with a sane fallback
const DEFAULT_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5001';

export const api = axios.create({
  baseURL: DEFAULT_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
  withCredentials: false, // set true only if you use cookies/sessions
});

// --- Helpers ---------------------------------------------------------------

// Optional: switch base URL at runtime if needed
export function setBaseURL(url) {
  if (url && typeof url === 'string') api.defaults.baseURL = url;
}

// Optional: attach/remove an Authorization header
export function setAuthToken(token) {
  if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  else delete api.defaults.headers.common['Authorization'];
}

// Uniform error surface
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg =
      err?.response?.data?.error ||
      err?.response?.data?.message ||
      err?.message ||
      'Request failed';
    return Promise.reject(new Error(msg));
  }
);

// Unwrap axios response.data
const unwrap = (p) => p.then((r) => r.data);

// --- Endpoints -------------------------------------------------------------

// Adapter-friendly unified call (works with Arvind’s /api/run or any adapter that returns { final })
export async function runProcurement(request_text, policy_text = '') {
  const data = await unwrap(api.post('/api/run', { request_text, policy_text }));
  const final = (data && data.final !== undefined) ? data.final : data;
  return { ok: data?.ok ?? true, final };
}

// Direct endpoints (use these if you’re not using /api/run)
export async function negotiate({ vendor, product, quantity }) {
  return unwrap(api.get('/negotiate', { params: { vendor, product, quantity } }));
}

export async function optimize(payload) {
  return unwrap(api.post('/optimize', payload));
}

export async function approve(payload) {
  return unwrap(api.post('/approve', payload));
}

export async function getKpis() {
  return unwrap(api.get('/analytics/kpis'));
}

// Quick health check (optional)
export async function health() {
  try {
    await api.get('/');
    return true;
  } catch {
    return false;
  }
}

export default api;
