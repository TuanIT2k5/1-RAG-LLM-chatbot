import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary-light text-primary border border-primary/20",
        citation:
          "bg-primary-light text-primary font-mono font-semibold border border-primary/30 hover:bg-primary hover:text-white cursor-pointer",
        success: "bg-emerald-50 text-status-success border border-emerald-200",
        warning: "bg-amber-50 text-status-warning border border-amber-200",
        danger: "bg-red-50 text-status-danger border border-red-200",
        muted: "bg-slate-100 text-text-muted border border-border-default",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };

