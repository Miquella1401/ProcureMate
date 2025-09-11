import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "http://127.0.0.1:5001",
  timeout: 30000
});

export async function runProcurement(request_text, policy_text = "") {
  const payload = { request_text, policy_text };
  const { data } = await api.post("/api/run", payload);
  return data; // { ok: true, final: {...} | "raw text" }
}
