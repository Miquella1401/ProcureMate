import { Bell, CircleUserRound } from "lucide-react";
import logo from "../assets/logo.svg";

export default function Header() {
  return (
    <header className="w-full">
      <div className="mx-auto max-w-6xl px-4 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src={logo} alt="ProcureAI" className="h-7 w-7" />
          <span className="font-semibold text-gray-900 text-lg">ProcureAI</span>
        </div>
        <div className="flex items-center gap-4">
          <button
            className="rounded-full p-2 hover:bg-gray-100 transition-colors"
            aria-label="Notifications"
            title="Notifications"
          >
            <Bell className="h-5 w-5 text-gray-600" />
          </button>
          <div className="h-9 w-9 rounded-full bg-gray-100 flex items-center justify-center">
            <CircleUserRound className="h-5 w-5 text-gray-600" />
          </div>
        </div>
      </div>
    </header>
  );
}
