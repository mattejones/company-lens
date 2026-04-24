import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Company Lens",
  description: "Enrich Companies House data with verified domain information",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="grid-bg min-h-screen">
        <Nav />
        <main className="max-w-6xl mx-auto px-6 pt-24 pb-16">{children}</main>
      </body>
    </html>
  );
}
