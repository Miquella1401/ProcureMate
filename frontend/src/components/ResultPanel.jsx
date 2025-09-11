export default function ResultPanel({ data, onClose }) {
  if (!data) return null;

  const pretty =
    typeof data.final === "object"
      ? JSON.stringify(data.final, null, 2)
      : data.final;

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/40 p-4">
      <div className="w-full md:max-w-3xl bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Result</h3>
          <button
            onClick={onClose}
            className="text-sm text-primary hover:underline"
          >
            Close
          </button>
        </div>
        <pre className="p-5 text-sm overflow-auto max-h-[70vh] bg-gray-50">
{pretty}
        </pre>
      </div>
    </div>
  );
}
