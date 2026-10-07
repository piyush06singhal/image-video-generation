import type { Metadata } from "next";
import { JetBrains_Mono, Outfit, Playfair_Display } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});
const playfairDisplay = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
});
const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title: "CinéEstate — AI Property Walkthrough Generation",
  description:
    "Transform property photographs into cinematic walkthrough videos. Gemini 2.5 Flash plans the route, then a swappable render engine (Google Veo, JSON2Video, or the built-in local renderer) produces the clips. Upload images, analyze scenes, plan routes, generate video.",
  keywords: ["real estate", "AI walkthrough", "property video", "Gemini", "Veo", "JSON2Video"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`h-full ${outfit.variable} ${playfairDisplay.variable} ${jetBrainsMono.variable}`}
      data-scroll-behavior="smooth"
    >
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
