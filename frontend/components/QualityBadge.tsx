"use client";

import React from "react";
import { ImageQualityResult } from "@/types/scene";
import { ShieldCheck, Sparkles, AlertCircle } from "lucide-react";

interface QualityBadgeProps {
  quality?: ImageQualityResult | null;
}

export const QualityBadge: React.FC<QualityBadgeProps> = ({ quality }) => {
  if (!quality) return null;

  const isGood = quality.status === "good";
  const isAcceptable = quality.status === "acceptable";

  const badgeClass = isGood
    ? "badge-success"
    : isAcceptable
    ? "badge-gold"
    : "badge-error";

  const label = isGood ? "High Quality" : isAcceptable ? "Acceptable" : "Low Quality";

  return (
    <div className="relative group/quality inline-block">
      <div className={`badge ${badgeClass} cursor-help transition-all flex items-center gap-1.5`}>
        {isGood ? (
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
        ) : (
          <AlertCircle className="w-3 h-3 text-amber-400" />
        )}
        <span>{label}</span>
      </div>

      {/* Floating Tooltip */}
      <div className="absolute top-full left-0 mt-2 hidden group-hover/quality:block z-50 p-3 rounded-xl text-xs w-56 space-y-1.5 font-normal pointer-events-none glass-gold border border-[var(--border-2)] text-[var(--text-1)] shadow-2xl">
        <div className="flex items-center justify-between font-semibold border-b border-[var(--border-1)] pb-1.5 mb-1.5">
          <span className="flex items-center gap-1 text-[var(--gold-2)]">
            <Sparkles className="w-3.5 h-3.5" /> Quality Metrics
          </span>
          <span className="capitalize text-[10px] font-mono text-[var(--gold-3)]">{quality.status}</span>
        </div>
        <div className="flex justify-between text-[var(--text-2)]">
          <span>Resolution:</span>
          <span className="font-mono text-[var(--text-1)] font-medium">{quality.resolution}</span>
        </div>
        <div className="flex justify-between text-[var(--text-2)]">
          <span>Sharpness:</span>
          <span className="font-mono text-emerald-400 font-medium">{(quality.sharpness_score * 100).toFixed(0)}%</span>
        </div>
        <div className="flex justify-between text-[var(--text-2)]">
          <span>Brightness:</span>
          <span className="font-mono text-[var(--gold-2)] font-medium">{(quality.brightness_score * 100).toFixed(0)}%</span>
        </div>
        <div className="flex justify-between text-[var(--text-2)]">
          <span>Contrast:</span>
          <span className="font-mono text-[var(--text-1)] font-medium">{(quality.contrast_score * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
};
