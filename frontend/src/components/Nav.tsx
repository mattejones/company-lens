"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Search" },
  { href: "/dataset", label: "Dataset" },
  { href: "/lookups", label: "Jobs" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-bg-border bg-bg-base/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-6 h-6 border border-accent rounded-sm flex items-center justify-center group-hover:bg-accent/10 transition-colors">
            <div className="w-2 h-2 bg-accent rounded-full" />
          </div>
          <span className="font-display font-700 text-sm tracking-widest uppercase text-text-primary">
            Company<span className="text-accent">Lens</span>
          </span>
        </Link>
        <div className="flex items-center gap-1">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`px-4 py-1.5 text-xs font-mono tracking-wider rounded transition-all ${
                path === l.href
                  ? "bg-accent/10 text-accent border border-accent/30"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
