import type { ReactNode } from "react";
import clsx from "clsx";

interface CardProps {
  title?: string;
  subtitle?: string;
  className?: string;
  children: ReactNode;
}

export function Card({ title, subtitle, className, children }: CardProps) {
  return (
    <div className={clsx("ds-card", className)}>
      {title && (
        <div className="mb-3">
          <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
          </h2>
          {subtitle && (
            <div className="mt-0.5 text-xs" style={{ color: "var(--text-tertiary)" }}>
              {subtitle}
            </div>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
