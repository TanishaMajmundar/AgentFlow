import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import Logo from "../Logo";
import Sidebar from "../Sidebar";
import ThemeToggle from "../ThemeToggle";

export default function AppLayout() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);

  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="min-h-screen lg:flex">
      {/* desktop sidebar */}
      <aside className="hidden w-[280px] shrink-0 lg:block print:hidden" aria-label="Sidebar">
        <div className="sticky top-0 h-screen"><Sidebar /></div>
      </aside>

      {/* mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-void/90 px-4 py-3 backdrop-blur lg:hidden print:hidden">
        <button onClick={() => setOpen(true)} aria-label="Open projects menu" aria-expanded={open} className="btn-ghost !p-2">
          <Menu size={18} />
        </button>
        <Logo size={17} to="/projects" />
        <ThemeToggle />
      </header>

      {/* mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden print:hidden" role="dialog" aria-modal="true" aria-label="Projects menu">
          <button aria-label="Close menu" onClick={() => setOpen(false)} className="absolute inset-0 animate-overlay-in bg-black/50" />
          <div className="absolute inset-y-0 left-0 w-[290px] max-w-[85vw] animate-slide-in">
            <Sidebar onNavigate={() => setOpen(false)} />
            <button onClick={() => setOpen(false)} aria-label="Close menu" className="absolute right-3 top-5 rounded-md p-1.5 text-muted transition hover:text-ink">
              <X size={18} />
            </button>
          </div>
        </div>
      )}

      <div className="min-w-0 flex-1">
        <div key={pathname} className="animate-page-in"><Outlet /></div>
      </div>
    </div>
  );
}
