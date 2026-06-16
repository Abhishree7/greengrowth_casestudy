import { Routes, Route, NavLink } from "react-router-dom";
import { FileText, History, BookOpen } from "lucide-react";
import SubmissionsPage from "./pages/SubmissionsPage";
import HistoryPage from "./pages/HistoryPage";
import PolicyPage from "./pages/PolicyPage";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-8">
        <div>
          <span className="text-lg font-semibold text-gray-900">Northwind Logistics</span>
          <span className="ml-2 text-sm text-gray-500">Expense Review</span>
        </div>
        <nav className="flex gap-1">
          <NavItem to="/" icon={<FileText size={16} />} label="New Submission" />
          <NavItem to="/history" icon={<History size={16} />} label="History" />
          <NavItem to="/policy" icon={<BookOpen size={16} />} label="Policy Q&A" />
        </nav>
      </header>

      <main className="flex-1 px-6 py-6 max-w-6xl mx-auto w-full">
        <Routes>
          <Route path="/" element={<SubmissionsPage />} />
          <Route path="/submissions/:id" element={<SubmissionsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/policy" element={<PolicyPage />} />
        </Routes>
      </main>
    </div>
  );
}

function NavItem({
  to,
  icon,
  label,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          isActive
            ? "bg-gray-100 text-gray-900"
            : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"
        }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}
