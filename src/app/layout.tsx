import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: {
    default: "AURUM · Rate Intelligence for Luxury Stays",
    template: "%s · AURUM",
  },
  description:
    "Track prepaid nightly rates for the world's finest hotels and get alerted the moment a stay drops below its historical average.",
  applicationName: "AURUM",
  openGraph: {
    title: "AURUM · Rate Intelligence for Luxury Stays",
    description:
      "Track prepaid nightly rates for the world's finest hotels and get alerted when a stay drops below its historical average.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0a0f",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="scroll-luxe flex min-h-dvh flex-col">
        {/* Fonts load at runtime in the browser (no build-time fetch) and
            degrade gracefully to system fonts. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          precedence="default"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Playfair+Display:wght@500;600;700&display=swap"
        />

        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
