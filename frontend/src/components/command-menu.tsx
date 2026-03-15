"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  FlaskConical,
  BarChart3,
  BookOpen,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

const ROUTES = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Participants", href: "/participants", icon: Users },
  { label: "Protocol Builder", href: "/protocol", icon: FlaskConical },
  { label: "Results", href: "/results", icon: BarChart3 },
  { label: "Paradigm Library", href: "/library", icon: BookOpen },
] as const;

export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const navigate = useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router]
  );

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          {ROUTES.map((route) => (
            <CommandItem
              key={route.href}
              onSelect={() => navigate(route.href)}
            >
              <route.icon className="mr-2 h-4 w-4" />
              <span>{route.label}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
