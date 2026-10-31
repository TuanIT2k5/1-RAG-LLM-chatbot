import * as React from "react";
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastVariant = "default" | "success" | "warning" | "danger";

export interface ToastItem {
  id: string;
  title: string;
  description?: string;
  variant?: ToastVariant;
}

interface ToastContextValue {
  toasts: ToastItem[];
  toast: (payload: Omit<ToastItem, "id">) => void;
  dismissToast: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | undefined>(
  undefined
);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const dismissToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const toast = React.useCallback(
    (payload: Omit<ToastItem, "id">) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((prev) => [...prev, { id, variant: "default", ...payload }]);
      window.setTimeout(() => {
        dismissToast(id);
      }, 4000);
    },
    [dismissToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, toast, dismissToast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
        {toasts.map((item) => {
          const variantStyles: Record<ToastVariant, string> = {
            default: "border-border-default bg-bg-surface text-text-primary",
            success: "border-emerald-200 bg-emerald-50/95 text-emerald-950",
            warning: "border-amber-200 bg-amber-50/95 text-amber-950",
            danger: "border-red-200 bg-red-50/95 text-red-950",
          };

          const IconComponent =
            item.variant === "success"
              ? CheckCircle2
              : item.variant === "warning"
              ? AlertTriangle
              : item.variant === "danger"
              ? XCircle
              : Info;

          const iconColor =
            item.variant === "success"
              ? "text-status-success"
              : item.variant === "warning"
              ? "text-status-warning"
              : item.variant === "danger"
              ? "text-status-danger"
              : "text-primary";

          return (
            <div
              key={item.id}
              className={cn(
                "pointer-events-auto flex items-start gap-3 rounded-xl border p-4 shadow-lg transition-all",
                variantStyles[item.variant || "default"]
              )}
            >
              <IconComponent className={cn("h-5 w-5 shrink-0 mt-0.5", iconColor)} />
              <div className="flex-1 text-sm">
                <p className="font-semibold">{item.title}</p>
                {item.description && (
                  <p className="mt-1 text-xs opacity-90">{item.description}</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => dismissToast(item.id)}
                className="rounded-md p-1 opacity-60 hover:opacity-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToastContext(): ToastContextValue {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToastContext phải được sử dụng bên trong ToastProvider");
  }
  return ctx;
}

