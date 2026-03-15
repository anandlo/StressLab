import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { AppSidebar } from "@/components/app-sidebar";
import { CommandMenu } from "@/components/command-menu";
import { BackButton } from "@/components/back-button";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "StressLab",
  description: "Cognitive stress induction research tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <Providers>
          <SidebarProvider>
            <AppSidebar />
            <SidebarInset>
              <header className="flex h-10 shrink-0 items-center gap-2 px-4">
                <SidebarTrigger className="-ml-1 text-muted-foreground hover:text-foreground" />
                <div className="h-4 w-px bg-border/60" />
                <BackButton />
                <kbd className="pointer-events-none hidden select-none items-center gap-1 rounded border bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground sm:inline-flex">
                  <span className="text-xs">⌘</span>K
                </kbd>
              </header>
              <div className="flex-1 overflow-auto px-8 py-6">
                {children}
              </div>
            </SidebarInset>
          </SidebarProvider>
          <CommandMenu />
        </Providers>
      </body>
    </html>
  );
}
