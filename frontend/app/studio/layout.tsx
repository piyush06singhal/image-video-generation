import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Studio — CinéEstate",
  description: "AI-powered property walkthrough generation studio. Upload images, analyze scenes, plan walkthroughs, and generate video.",
};

export default function StudioLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
