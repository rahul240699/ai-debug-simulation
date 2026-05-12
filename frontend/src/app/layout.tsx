import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prove AI — Diagnosis Dashboard",
  description: "Agent observability and trace diagnosis for dungeon simulation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-zinc-100 antialiased min-h-screen" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
