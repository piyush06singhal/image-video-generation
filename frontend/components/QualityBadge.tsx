"use client";

import React from "react";
import { ImageQualityResult } from "@/types/scene";
import { ShieldCheck, Sparkles } from "lucide-react";

interface QualityBadgeProps {
  quality?: ImageQualityResult | null;
}

export const QualityBadge: React.FC<QualityBadgeProps> = ({ quality }) => {
  if (!quality) return null;

  const isGood = quality.status === "good";
  const isAcceptable = quality.status === "acceptable";

  const badgeStyle = isGood
    ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.2)]"
    : isAcceptable
    ? "bg-amber-950/80 text-amber-300 border-amber-500/30 shadow-[0_0_12px_rgba(245,158,11,0.2)]"
    : "bg-rose-950/80 text-rose-300 border-rose-500/30 shadow-[0_0_12px_rgba(244,63,94,0.2)]";

  const dotColor = isGood
    ? "bg-emerald-400"
    : isAcceptable
    ? "bg-amber-400"
    : "bg-rose-400";

  const label = isGood ? "Good Quality" : isAcceptable ? "Acceptable" : "Low Quality";

  return (
    <div
      className={`group/quality relative flex items-center gap-1.5 text-[10.5px] font-medium px-2 py-0.5 rounded-full border backdrop-blur-md cursor-help transition-all ${badgeStyle}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} animate-pulse`} />
      <ShieldCheck className="w-3 h-3" />
      <span>{label}</span>

      {/* Floating Detailed Metrics Tooltip on Hover */}
      <div className="absolute top-full left-0 mt-2 hidden group-hover/quality:block z-50 p-3 rounded-xl shadow-2xl text-[11px] w-52 space-y-1.5 font-normal pointer-events-none glass-card-elevated border border-slate-700/60 bg-slate-900/95 text-slate-200">
        <div className="flex items-center justify-between font-semibold text-slate-100 border-b border-slate-700/60 pb-1 mb-1">
          <span className="flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-indigo-400" /> Quality Metrics
          </span>
          <span className="capitalize text-[10px] text-indigo-400 font-mono">{quality.status}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Resolution:</span>
          <span className="font-mono text-slate-200">{quality.resolution}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Sharpness:</span>
          <span className="font-mono text-emerald-400">{(quality.sharpness_score * 100).toFixed(0)}%</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Brightness:</span>
          <span className="font-mono text-amber-300">{(quality.brightness_score * 100).toFixed(0)}%</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Contrast:</span>
          <span className="font-mono text-indigo-300">{(quality.contrast_score * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
};
