import clsx from "clsx";
import React, { ReactNode } from "react";

interface GlassCardProps {
    children: ReactNode;
    className?: string;
    hoverEffect?: boolean;
    intensity?: "low" | "medium" | "high";
}

export function GlassCard({
    children,
    className,
    hoverEffect = true,
    intensity = "medium",
}: GlassCardProps) {
    const baseStyles = "relative overflow-hidden rounded-2xl border transition-all duration-300";

    const intensityStyles = {
        low: "bg-black/20 border-white/5 backdrop-blur-md",
        medium: "bg-white/[0.03] border-white/10 backdrop-blur-xl shadow-lg",
        high: "bg-white/[0.07] border-white/15 backdrop-blur-2xl shadow-xl",
    };

    const hoverStyles = hoverEffect
        ? "hover:border-brand-500/30 hover:bg-white/[0.06] hover:shadow-brand-500/10 hover:-translate-y-1"
        : "";

    return (
        <div
            className={clsx(
                baseStyles,
                intensityStyles[intensity],
                hoverStyles,
                "group",
                className
            )}
        >
            {/* Spotlight Gradient Layer */}
            <div className="pointer-events-none absolute -inset-px opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                style={{
                    background: `radial-gradient(600px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(99, 102, 241, 0.15), transparent 40%)`
                }}
            />

            {/* Content */}
            <div className="relative z-10">{children}</div>
        </div>
    );
}
