const SAMPLES = [
  "Find a catering service for a 100-person event",
  "Renew our software license for project management tools",
  "Order new ergonomic office chairs"
];

export default function SuggestionPills({ onPick }) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
      {SAMPLES.map((s) => (
        <button
          key={s}
          onClick={() => onPick(s)}
          className="px-4 py-2 rounded-full bg-white/90 hover:bg-white text-gray-700 text-sm shadow-soft border border-gray-200 transition-all"
        >
          “{s}”
        </button>
      ))}
    </div>
  );
}
