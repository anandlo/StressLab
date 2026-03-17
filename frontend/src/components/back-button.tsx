"use client";

import { usePathname, useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

// Pages where the back button should not appear
const ROOT_PAGES = ["/", "/library", "/participants", "/protocol", "/results", "/projects", "/support", "/session"];

export function BackButton() {
  const pathname = usePathname();
  const router = useRouter();

  if (ROOT_PAGES.includes(pathname)) return null;

  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground"
      onClick={() => router.back()}
    >
      <ChevronLeft className="h-4 w-4" />
      <span className="text-xs">Back</span>
    </Button>
  );
}
