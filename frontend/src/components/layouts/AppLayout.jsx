import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { LogOut, Plus } from "lucide-react";
import Logo from "../Logo";
import { useAuth } from "../../context/AuthContext";
import ThemeToggle from "../ThemeToggle";

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const navClass = ({ isActive }) =>
    `rounded-md px-3 py-1.5 text-sm transition ${isActive ? "bg-panel2 text-ink" : "text-muted hover:text-ink"}`;

  return (
    <div className="bg-grid min-h-screen">
      <header className="sticky top-0 z-30 border-b border-edge bg-void/85 backdrop-blur print:hidden">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-8">
            <Logo size={17} to="/projects" />
            <nav className="hidden items-center gap-1 sm:flex" aria-label="Main">
              <NavLink to="/projects" end className={navClass}>Projects</NavLink>
              <NavLink to="/projects/new" className={navClass}>New project</NavLink>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/projects/new" className="btn-primary !px-3.5 !py-2 sm:hidden" aria-label="New project">
              <Plus size={15} />
            </Link>
            <span className="hidden font-mono text-xs text-muted md:inline">{user?.email}</span>
            <ThemeToggle />
            <button
              onClick={() => { logout(); navigate("/"); }}
              className="btn-ghost !px-3 !py-2 !text-xs"
            >
              <LogOut size={14} /> Log out
            </button>
          </div>
        </div>
      </header>
      {/* keyed by route so every page change plays the entrance animation */}
      <div key={pathname} className="animate-page-in">
        <Outlet />
      </div>
    </div>
  );
}
