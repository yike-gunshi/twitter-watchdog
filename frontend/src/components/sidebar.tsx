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
      <div className="flex items-center gap-2.5 px-2 mb-8">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <Radio className="h-4 w-4 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-sm font-semibold leading-tight">Twitter Watchdog</h1>
          <p className="text-[11px] text-muted-foreground leading-tight">信息监控助手</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 flex-1">
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
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Theme toggle */}
      <div className="flex items-center justify-between border-t pt-4 mt-4">
        <span className="text-xs text-muted-foreground">切换主题</span>
        <ThemeToggle />
      </div>
    </>
  );

  return (
    <>
      {/* Mobile toggle */}
      <div className="fixed top-0 left-0 right-0 z-50 flex h-14 items-center border-b bg-background/80 backdrop-blur-sm px-4 lg:hidden">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </Button>
        <div className="flex items-center gap-2 ml-2">
          <Radio className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold">Twitter Watchdog</span>
        </div>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-64 border-r bg-background p-4 pt-16 transition-transform lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">{navContent}</div>
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:w-60 lg:flex-col lg:border-r lg:bg-background/50 lg:p-4">
        <div className="flex h-full flex-col">{navContent}</div>
      </aside>
    </>
  );
}
