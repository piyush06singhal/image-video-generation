"use client";

import React from "react";
import Link from "next/link";
import { Film, Wifi, WifiOff, RefreshCw, ArrowLeft } from "lucide-react";

interface StudioHeaderProps {
  isBackendHealthy: boolean | null;
  onRetryHealth: () => void;
  isCheckingHealth: boolean;
}

export const StudioHeader: React.FC<StudioHeaderProps> = ({
  isBackendHealthy,
  onRetryHealth,
  isCheckingHealth,
}) => {
  return (
    <header
      className="sticky top-0 z-40"
      style={{
        background: "rgba(8,10,13,0.95)",
        borderBottom: "1px solid rgba(212,168,83,0.08)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
      }}
    >
      {/* Gold accent line */}
      <div
        className="h-px w-full"
        style={{
          background: "linear-gradient(90deg, transparent, #d4a853 30%, #e8c07a 60%, transparent)",
          opacity: 0.5,
        }}
      />

      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Left — back + brand */}
        <div className="flex items-center gap-5">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs text-[var(--text-3)] hover:text-[var(--gold-1)] transition-colors group"
          >
            <ArrowLeft size={13} className="group-hover:-translate-x-0.5 transition-transform" />
            <span>Home</span>
          </Link>

          <div className="w-px h-4 bg-[var(--border-0)]" />

          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, #d4a853, #8a5e20)" }}
            >
              <Film size={15} className="text-[#080a0d]" />
            </div>
            <div>
              <p className="text-sm font-bold font-display text-[var(--text-1)] leading-none">
                Ciné<span className="text-gold-subtle">Estate</span>
              </p>
              <p className="text-[10px] text-[var(--text-3)] leading-none mt-0.5">
                Generation Studio
              </p>
            </div>
          </div>
        </div>

        {/* Right — backend status */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={isBackendHealthy === false ? onRetryHealth : undefined}
            disabled={isCheckingHealth}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full transition-all"
            style={{
              background:
                isBackendHealthy === true
                  ? "rgba(74,222,128,0.08)"
                  : isBackendHealthy === false
                  ? "rgba(248,113,113,0.08)"
                  : "rgba(100,116,139,0.08)",
              border:
                isBackendHealthy === true
                  ? "1px solid rgba(74,222,128,0.2)"
                  : isBackendHealthy === false
                  ? "1px solid rgba(248,113,113,0.2)"
                  : "1px solid rgba(100,116,139,0.15)",
              color:
                isBackendHealthy === true
                  ? "#4ade80"
                  : isBackendHealthy === false
                  ? "#f87171"
                  : "#94a3b8",
              cursor: isBackendHealthy === false ? "pointer" : "default",
            }}
          >
            {isCheckingHealth ? (
              <span
                className="w-3 h-3 rounded-full border-2 border-current border-t-transparent animate-spin"
                style={{ display: "inline-block" }}
              />
            ) : isBackendHealthy === true ? (
              <Wifi size={12} />
            ) : (
              <WifiOff size={12} />
            )}
            <span className="font-medium">
              {isBackendHealthy === true
                ? "API Live"
                : isBackendHealthy === false
                ? "Offline"
                : "Connecting"}
            </span>
            {isBackendHealthy === false && !isCheckingHealth && (
              <RefreshCw size={11} />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
