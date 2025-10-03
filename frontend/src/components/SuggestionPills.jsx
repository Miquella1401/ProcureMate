const SAMPLES = [
 
  "request_text We need 50 laptops for our company with a budget of $500 each by September policy_text : Maximum unit price must be 500 USD, and delivery must be under 10 days",
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
