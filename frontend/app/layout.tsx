import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CinéEstate — AI Property Walkthrough Generation",
  description:
    "Transform property photographs into cinematic walkthrough videos using Gemini AI and Google Veo. Upload images, analyze scenes, plan routes, generate video.",
  keywords: ["real estate", "AI walkthrough", "property video", "Gemini", "Veo"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full" data-scroll-behavior="smooth">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700;800;900&family=Playfair+Display:ital,wght@0,400;0,600;0,700;0,800;1,400;1,600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
