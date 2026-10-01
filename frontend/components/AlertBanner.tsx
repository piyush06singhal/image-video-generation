"use client";

import React from "react";
import { AlertCircle, CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

export type AlertType = "info" | "success" | "warning" | "error";

interface AlertBannerProps {
  type: AlertType;
  title?: string;
  message: string;
  onDismiss?: () => void;
}

const ALERT_CONFIG: Record<
  AlertType,
  { bg: string; border: string; iconColor: string; titleColor: string; icon: React.ReactNode }
> = {
  info: {
    bg: "rgba(212, 168, 83, 0.08)",
    border: "rgba(212, 168, 83, 0.25)",
    iconColor: "var(--gold-2)",
    titleColor: "var(--gold-3)",
    icon: <Info className="w-4.5 h-4.5 shrink-0" />,
  },
  success: {
    bg: "rgba(74, 222, 128, 0.08)",
    border: "rgba(74, 222, 128, 0.25)",
    iconColor: "#4ade80",
    titleColor: "#86efac",
    icon: <CheckCircle2 className="w-4.5 h-4.5 shrink-0" />,
  },
  warning: {
    bg: "rgba(251, 191, 36, 0.08)",
    border: "rgba(251, 191, 36, 0.25)",
    iconColor: "#fbbf24",
    titleColor: "#fde047",
    icon: <AlertTriangle className="w-4.5 h-4.5 shrink-0" />,
  },
  error: {
    bg: "rgba(248, 113, 113, 0.08)",
    border: "rgba(248, 113, 113, 0.25)",
    iconColor: "#f87171",
    titleColor: "#fca5a5",
    icon: <AlertCircle className="w-4.5 h-4.5 shrink-0" />,
  },
};

export const AlertBanner: React.FC<AlertBannerProps> = ({
  type,
  title,
  message,
  onDismiss,
}) => {
  const cfg = ALERT_CONFIG[type];

  return (
    <div
      className="anim-fade-up flex items-start gap-3 p-4 rounded-xl backdrop-blur-md"
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
      }}
    >
      <span style={{ color: cfg.iconColor, marginTop: "1px" }}>
        {cfg.icon}
      </span>

      <div className="grow min-w-0 text-sm">
        {title && (
          <p className="font-semibold text-sm mb-0.5" style={{ color: cfg.titleColor }}>
            {title}
          </p>
        )}
        <p className="leading-relaxed text-xs text-[var(--text-2)]">
          {message}
        </p>
      </div>

      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="p-1 rounded-lg transition-all hover:bg-white/5 shrink-0 text-[var(--text-3)] hover:text-white"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
