"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

function NavLink({ href, children }: { href: string; children: ReactNode }) {
  const path = usePathname();
  const active =
    href === "/" ? path === "/" : path === href || path.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      className={
        active ? "text-amber-900 underline decoration-amber-400" : "text-stone-600 hover:text-stone-900"
      }
    >
      {children}
    </Link>
  );
}

export default function SiteHeader() {
  return (
    <header className="border-b border-stone-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-3">
        <Link href="/" className="flex items-baseline gap-3 hover:opacity-90">
          <span className="font-serif text-lg font-semibold text-stone-900">Julia Reader</span>
          <span className="text-sm text-stone-500">Next.js demo</span>
        </Link>
        <nav className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-medium">
          <NavLink href="/">Chronicle</NavLink>
          <NavLink href="/whitepaper">White paper</NavLink>
          <NavLink href="/playground">Playground</NavLink>
        </nav>
      </div>
    </header>
  );
}
