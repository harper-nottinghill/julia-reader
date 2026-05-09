import SiteHeader from "@/components/SiteHeader";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Julia Reader · Next.js demo",
  description:
    "Bundled Dune Chronicle (static Reader output) plus an optional playground that runs the Python harness.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
