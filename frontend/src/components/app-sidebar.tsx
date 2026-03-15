"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  FlaskConical,
  BarChart3,
  BookOpen,
  Brain,
  FolderOpen,
  LogIn,
  LogOut,
  ShieldCheck,
  LifeBuoy,
  User,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Participants", href: "/participants", icon: Users },
  { label: "Protocol", href: "/protocol", icon: FlaskConical },
  { label: "Sessions", href: "/results", icon: BarChart3 },
  { label: "Library", href: "/library", icon: BookOpen },
  { label: "Projects", href: "/projects", icon: FolderOpen },
  { label: "Support", href: "/support", icon: LifeBuoy },
] as const;

export function AppSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <Sidebar>
      <SidebarHeader className="px-4 pt-5 pb-4">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shrink-0">
            <Brain className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-[15px] font-bold tracking-tight leading-tight">
              StressLab
            </span>
            <span className="text-[10px] text-muted-foreground leading-tight">
              Cognitive Research Tool
            </span>
          </div>
        </Link>
      </SidebarHeader>

      <SidebarContent className="px-2">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      isActive={isActive}
                      render={
                        <Link
                          href={item.href}
                          className={cn(
                            "flex items-center gap-2.5",
                            isActive && "font-medium"
                          )}
                        />
                      }
                    >
                        <item.icon className="h-4 w-4 shrink-0" />
                        <span className="text-[13px]">{item.label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-4 py-3 space-y-2">
        {user ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
              <User className="h-4 w-4 shrink-0 text-primary" />
              <span className="text-[12px] font-medium leading-tight truncate">
                {user.email}
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
              onClick={logout}
            >
              <LogOut className="h-4 w-4" />
              <span className="text-[12px]">Sign out</span>
            </Button>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center gap-2 rounded-md border border-dashed border-muted-foreground/30 px-3 py-2 text-sm text-muted-foreground hover:border-primary/60 hover:text-foreground transition-colors"
          >
            <LogIn className="h-4 w-4 shrink-0" />
            <span className="text-[12px] font-medium leading-tight">Sign in</span>
          </Link>
        )}
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-muted-foreground/60">v2.0</span>
          <ThemeToggle />
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
