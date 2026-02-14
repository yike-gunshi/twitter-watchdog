"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Wrench,
  Radio,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useState } from "react";

const navItems = [
  { href: "/", label: "信息中心", icon: LayoutDashboard },
  { href: "/workbench", label: "工作台", icon: Wrench },
];

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navContent = (
    <>
      {/* Logo */}
      <div className="flex items-center gap-3 px-3 mb-8">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/20">
          <Radio className="h-4.5 w-4.5 text-white" />
          <div className="absolute inset-0 rounded-xl bg-white/10" />
        </div>
        <div>
          <h1 className="text-sm font-bold leading-tight tracking-tight">Twitter Watchdog</h1>
          <p className="text-[10px] text-muted-foreground/70 leading-tight">信息监控助手</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 flex-1 px-1">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 cursor-pointer",
                isActive
                  ? "bg-primary/10 text-primary shadow-sm shadow-primary/5 dark:bg-primary/15 dark:shadow-primary/10"
                  : "text-muted-foreground hover:bg-accent/80 hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-4 w-4", isActive && "drop-shadow-sm")} />
              {item.label}
              {isActive && (
                <div className="ml-auto h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Theme toggle */}
      <div className="flex items-center justify-between border-t border-border/50 pt-4 mt-4 px-2">
        <span className="text-[11px] text-muted-foreground/60">主题</span>
        <ThemeToggle />
      </div>
    </>
  );

  return (
    <>
      {/* Mobile toggle */}
      <div className="fixed top-0 left-0 right-0 z-50 flex h-14 items-center border-b border-border/50 bg-background/80 backdrop-blur-xl px-4 lg:hidden">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 cursor-pointer"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </Button>
        <div className="flex items-center gap-2 ml-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600">
            <Radio className="h-3 w-3 text-white" />
          </div>
          <span className="text-sm font-bold">Twitter Watchdog</span>
        </div>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-64 border-r border-border/50 bg-background/95 backdrop-blur-xl p-4 pt-16 transition-transform lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">{navContent}</div>
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:w-60 lg:flex-col lg:border-r lg:border-border/50 lg:bg-card/30 lg:backdrop-blur-xl lg:p-4">
        <div className="flex h-full flex-col">{navContent}</div>
      </aside>
    </>
  );
}
