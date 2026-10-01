"use client";

import React from "react";
import Link from "next/link";
import { Film, Wifi, WifiOff, RefreshCw, ChevronLeft } from "lucide-react";

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
    <header className="sticky top-0 z-50" style={{ background: "var(--nav-bg)" }}>
      {/* Signature gold accent line */}
      <div
        className="h-[2px] w-full"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, rgba(184,136,43,0.7) 25%, #d4a843 50%, rgba(184,136,43,0.7) 75%, transparent 100%)",
        }}
      />

      <div
        className="max-w-7xl mx-auto px-6 sm:px-10 h-16 flex items-center justify-between"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}
      >
        {/* Left — back + brand */}
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs font-semibold transition-all duration-200 px-3 py-1.5 rounded-lg group"
            style={{ color: "rgba(148,163,184,0.7)" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#d4a843";
              e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "rgba(148,163,184,0.7)";
              e.currentTarget.style.background = "transparent";
            }}
          >
            <ChevronLeft size={14} className="group-hover:-translate-x-0.5 transition-transform" />
            <span>Home</span>
          </Link>

          <div className="w-px h-5" style={{ background: "rgba(255,255,255,0.10)" }} />

          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{
                background: "linear-gradient(135deg, #d4a843 0%, #a0711a 100%)",
                boxShadow: "0 3px 12px rgba(184,136,43,0.35)",
              }}
            >
              <Film size={17} className="text-[#0d1220]" />
            </div>
            <div>
              <p className="text-base font-bold font-display leading-none text-white">
                Ciné<span style={{ color: "#d4a843" }}>Estate</span>
              </p>
              <p
                className="text-[9px] tracking-[0.22em] uppercase font-semibold leading-none mt-0.5"
                style={{ color: "rgba(212,168,67,0.60)" }}
              >
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
            className="flex items-center gap-1.5 text-xs px-3.5 py-1.5 rounded-full font-medium transition-all duration-200"
            style={{
              background:
                isBackendHealthy === true
                  ? "rgba(74,222,128,0.09)"
                  : isBackendHealthy === false
                  ? "rgba(248,113,113,0.09)"
                  : "rgba(100,116,139,0.09)",
              border:
                isBackendHealthy === true
                  ? "1px solid rgba(74,222,128,0.22)"
                  : isBackendHealthy === false
                  ? "1px solid rgba(248,113,113,0.22)"
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
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <Wifi size={12} />
              </>
            ) : (
              <WifiOff size={12} />
            )}
            <span>
              {isBackendHealthy === true
                ? "API Live"
                : isBackendHealthy === false
                ? "Offline"
                : "Connecting…"}
            </span>
            {isBackendHealthy === false && !isCheckingHealth && (
              <RefreshCw size={11} className="ml-0.5" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
