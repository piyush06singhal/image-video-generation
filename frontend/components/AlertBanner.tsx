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

const ALERT_STYLES: Record<AlertType, { bg: string; border: string; iconColor: string; titleColor: string; msgColor: string }> = {
  info: {
    bg: "rgba(99, 102, 241, 0.08)",
    border: "rgba(99, 102, 241, 0.2)",
    iconColor: "#818cf8",
    titleColor: "#a5b4fc",
    msgColor: "#94a3b8",
  },
  success: {
    bg: "rgba(16, 185, 129, 0.08)",
    border: "rgba(16, 185, 129, 0.2)",
    iconColor: "#34d399",
    titleColor: "#6ee7b7",
    msgColor: "#94a3b8",
  },
  warning: {
    bg: "rgba(245, 158, 11, 0.08)",
    border: "rgba(245, 158, 11, 0.2)",
    iconColor: "#fbbf24",
    titleColor: "#fcd34d",
    msgColor: "#94a3b8",
  },
  error: {
    bg: "rgba(244, 63, 94, 0.08)",
    border: "rgba(244, 63, 94, 0.2)",
    iconColor: "#fb7185",
    titleColor: "#fda4af",
    msgColor: "#94a3b8",
  },
};

const ICONS: Record<AlertType, React.ReactNode> = {
  info: <Info className="w-4.5 h-4.5 shrink-0" />,
  success: <CheckCircle2 className="w-4.5 h-4.5 shrink-0" />,
  warning: <AlertTriangle className="w-4.5 h-4.5 shrink-0" />,
  error: <AlertCircle className="w-4.5 h-4.5 shrink-0" />,
};

export const AlertBanner: React.FC<AlertBannerProps> = ({
  type,
  title,
  message,
  onDismiss,
}) => {
  const s = ALERT_STYLES[type];

  return (
    <div
      className="animate-slide-up flex items-start gap-3 p-4 rounded-xl"
      style={{
        background: s.bg,
        border: `1px solid ${s.border}`,
      }}
    >
      <span style={{ color: s.iconColor, marginTop: "1px" }}>
        {ICONS[type]}
      </span>

      <div className="grow min-w-0 text-sm">
        {title && (
          <p className="font-semibold text-sm mb-0.5" style={{ color: s.titleColor }}>
            {title}
          </p>
        )}
        <p className="leading-relaxed text-xs" style={{ color: s.msgColor }}>
          {message}
        </p>
      </div>

      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="p-1 rounded-lg transition-all hover:bg-white/5 shrink-0"
          style={{ color: "#475569" }}
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
