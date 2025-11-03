"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  BookOpen,
  ClipboardList,
  MessageSquare,
  Megaphone,
  BarChart3,
  MessageCircle,
} from "lucide-react";

const sidebarItems = [
  {
    id: "overview",
    label: "儀表板",
    icon: LayoutDashboard,
    href: "/dashboard",
  },
  {
    id: "courses",
    label: "課程管理",
    icon: BookOpen,
    href: "/dashboard/courses",
  },
  {
    id: "questions",
    label: "提問審核",
    icon: ClipboardList,
    href: "/dashboard/questions",
  },
  { id: "qa", label: "Q&A 管理", icon: MessageSquare, href: "/dashboard/qa" },
  {
    id: "announcements",
    label: "公告管理",
    icon: Megaphone,
    href: "/dashboard/announcements",
  },
  {
    id: "statistics",
    label: "統計報表",
    icon: BarChart3,
    href: "/dashboard/statistics",
  },
  {
    id: "line",
    label: "Line 整合",
    icon: MessageCircle,
    href: "/dashboard/line-integration",
  },
];

export function DashboardSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-card border-r border-border p-6 hidden md:block">
      <nav className="space-y-2">
        {sidebarItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <Link
              key={item.id}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
                isActive
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-foreground hover:bg-secondary"
              )}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
