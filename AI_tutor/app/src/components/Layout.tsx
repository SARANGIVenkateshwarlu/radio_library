import { Link, useLocation } from "react-router";
import { Home, BookMarked, RotateCcw, GraduationCap } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Home", icon: Home },
  { to: "/phrasebook", label: "Phrasebook", icon: BookMarked },
  { to: "/review", label: "Review", icon: RotateCcw },
  { to: "/resources", label: "Resources", icon: GraduationCap },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const loc = useLocation();
  return (
    <div className="min-h-screen bg-[#0b0f14] text-zinc-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,rgba(45,212,191,0.07),transparent_55%)]" />
      <header className="sticky top-0 z-20 border-b border-white/5 bg-[#0b0f14]/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-jade-500/20 text-jade-300 text-lg">
              粤
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold tracking-wide">Real AI Tutor</p>
              <p className="text-[11px] text-zinc-500">English → Hong Kong Cantonese</p>
            </div>
          </Link>
          <nav className="flex items-center gap-1">
            {NAV.map((n) => {
              const active = loc.pathname === n.to;
              return (
                <Link
                  key={n.to}
                  to={n.to}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs transition-colors",
                    active ? "bg-jade-500/15 text-jade-200" : "text-zinc-400 hover:text-zinc-200",
                  )}
                >
                  <n.icon className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">{n.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <main className="relative mx-auto max-w-5xl px-4 pb-20">{children}</main>
    </div>
  );
}
