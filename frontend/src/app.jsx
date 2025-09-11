import { useState } from "react";
import Header from "./components/Header.jsx";
import Hero from "./components/Hero.jsx";
import ResultPanel from "./components/ResultPanel.jsx";
import { runProcurement } from "./lib/api.js";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function handleSubmit(requestText) {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await runProcurement(
        requestText,
        // you can pass a default policy text or leave empty for backend default
        ""
      );
      setResult(data);
    } catch (e) {
      setError(
        e?.response?.data?.message ||
          e?.message ||
          "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-full font-sans">
      <Header />
      <Hero onSubmit={handleSubmit} loading={loading} />

      {error && (
        <div className="max-w-3xl mx-auto px-4">
          <div className="bg-red-50 text-red-700 rounded-xl px-4 py-3 border border-red-200">
            {error}
          </div>
        </div>
      )}

      <ResultPanel data={result} onClose={() => setResult(null)} />
    </div>
  );
}
