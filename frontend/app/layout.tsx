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
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
