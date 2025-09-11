import { useState } from "react";
import { ArrowRight } from "lucide-react";
import SuggestionPills from "./SuggestionPills.jsx";

export default function Hero({ onSubmit, loading }) {
  const [text, setText] = useState("");

  const placeholder =
    "e.g., 'Source 500 laptops with i7 processors and 16GB RAM for the engineering team'";

  return (
    <section className="relative">
      <div className="gradient-blob"></div>

      <div className="mx-auto max-w-6xl px-4 pt-10 pb-16 sm:pt-16 sm:pb-24">
        <div className="text-center">
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-gray-900">
            Procurement, Simplified.
          </h1>
          <p className="mt-4 text-gray-600 text-lg max-w-2xl mx-auto">
            Describe your procurement needs below and let our AI handle the rest.
            From sourcing to purchase orders, we&apos;ve got you covered.
          </p>
        </div>

        <div className="mt-8 flex justify-center">
          <div className="hero-pane w-full sm:w-[720px] rounded-full shadow-soft border border-gray-200 p-2 pr-2 flex items-center gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && text.trim() && !loading) {
                  onSubmit(text.trim());
                }
              }}
              className="flex-1 bg-transparent outline-none px-4 py-3 text-gray-800 placeholder:text-gray-400"
              placeholder={placeholder}
            />
            <button
              disabled={!text.trim() || loading}
              onClick={() => onSubmit(text.trim())}
              className="rounded-full bg-primary text-white px-5 py-2.5 font-medium flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? "Working..." : "Generate"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        <SuggestionPills
          onPick={(sample) => {
            // autofill the input and optionally auto-run
            const input = document.querySelector("input[placeholder^='e.g.,']");
            if (input) input.value = sample;
            // emulate controlled update:
            setText(sample);
          }}
        />

        <div className="mt-10 mx-auto max-w-3xl rounded-3xl overflow-hidden shadow-soft">
          <div className="h-52 sm:h-64 bg-[url('https://images.unsplash.com/photo-1519389950473-47ba0277781c?q=80&w=1469&auto=format&fit=crop')] bg-cover bg-center opacity-90" />
        </div>

        <p className="text-center text-xs text-gray-500 mt-8">
          © {new Date().getFullYear()} ProcureAI. All rights reserved.
        </p>
      </div>
    </section>
  );
}
