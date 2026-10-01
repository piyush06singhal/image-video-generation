"use client";

import React from "react";
import { Building2, RefreshCw, Wifi, WifiOff } from "lucide-react";

interface HeaderProps {
  isBackendHealthy: boolean | null;
  onRetryHealth: () => void;
  isCheckingHealth: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  isBackendHealthy,
  onRetryHealth,
  isCheckingHealth,
}) => {
  return (
    <header
      className="sticky top-0 z-40 border-b"
      style={{
        background: "#0e131d",
        borderColor: "rgba(255, 255, 255, 0.08)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
      }}
    >
      {/* Top accent line */}
      <div
        className="h-[2px] w-full"
        style={{
          background:
            "linear-gradient(90deg, transparent, #c28b2e 30%, #d9a443 60%, transparent)",
        }}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3.5">
          {/* Logo */}
          <div
            className="relative w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-md shadow-amber-950/40"
            style={{
              background: "linear-gradient(135deg, #d9a443, #a66e1b)",
            }}
          >
            <Building2 className="w-5 h-5 text-slate-950 font-bold" />
            {/* Animated corner dot */}
            <span
              className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2"
              style={{
                background: isBackendHealthy === true ? "#16a34a" : isBackendHealthy === false ? "#dc2626" : "#94a3b8",
                borderColor: "#0e131d",
                boxShadow: isBackendHealthy === true ? "0 0 6px rgba(22,163,74,0.8)" : "none",
              }}
            />
          </div>

          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-base font-bold tracking-tight font-display text-white">
                Ciné<span className="text-amber-400">Estate</span>
              </h1>
              <span
                className="text-[10px] font-semibold tracking-widest uppercase px-2 py-0.5 rounded-full"
                style={{
                  background: "rgba(194, 139, 46, 0.15)",
                  color: "#d9a443",
                  border: "1px solid rgba(194, 139, 46, 0.3)",
                }}
              >
                PRO
              </span>
            </div>
            <p className="text-[11px] hidden sm:block text-slate-400">
              Transform property photographs into cinematic walkthroughs
            </p>
          </div>
        </div>

        {/* Right side: Status */}
        <div className="flex items-center gap-3">
          {/* Backend Status Pill */}
          <div
            className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full transition-all"
            style={{
              background:
                isBackendHealthy === true
                  ? "rgba(16, 185, 129, 0.08)"
                  : isBackendHealthy === false
                  ? "rgba(244, 63, 94, 0.08)"
                  : "rgba(100, 116, 139, 0.08)",
              border:
                isBackendHealthy === true
                  ? "1px solid rgba(16, 185, 129, 0.2)"
                  : isBackendHealthy === false
                  ? "1px solid rgba(244, 63, 94, 0.2)"
                  : "1px solid rgba(100, 116, 139, 0.15)",
              color:
                isBackendHealthy === true
                  ? "#34d399"
                  : isBackendHealthy === false
                  ? "#fb7185"
                  : "#94a3b8",
            }}
          >
            {isBackendHealthy === true ? (
              <Wifi className="w-3.5 h-3.5" />
            ) : isBackendHealthy === false ? (
              <WifiOff className="w-3.5 h-3.5" />
            ) : (
              <span
                className="w-3 h-3 rounded-full border-2 border-current border-t-transparent animate-spin"
                style={{ display: "inline-block" }}
              />
            )}
            <span className="font-medium">
              {isBackendHealthy === true
                ? "API Connected"
                : isBackendHealthy === false
                ? "Backend Offline"
                : "Connecting..."}
            </span>

            {isBackendHealthy === false && (
              <button
                type="button"
                onClick={onRetryHealth}
                disabled={isCheckingHealth}
                className="ml-0.5 hover:opacity-70 transition-opacity"
                title="Retry connection"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${isCheckingHealth ? "animate-spin" : ""}`}
                />
              </button>
            )}
          </div>

          {/* Academic badge */}
          <span
            className="hidden sm:flex text-[10px] font-medium tracking-wide uppercase px-2.5 py-1 rounded-full"
            style={{
              background: "rgba(148, 163, 184, 0.06)",
              color: "#475569",
              border: "1px solid rgba(148, 163, 184, 0.1)",
            }}
          >
            Minor Project
          </span>
        </div>
      </div>
    </header>
  );
};
