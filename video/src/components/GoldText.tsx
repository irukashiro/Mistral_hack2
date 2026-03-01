import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";

export const FadeIn: React.FC<{
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  style?: React.CSSProperties;
}> = ({ children, delay = 0, duration = 20, style }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [delay, delay + duration], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div style={{ opacity, transform: `translateY(${translateY}px)`, ...style }}>
      {children}
    </div>
  );
};

export const GoldDivider: React.FC<{ delay?: number }> = ({ delay = 0 }) => {
  const frame = useCurrentFrame();
  const scaleX = interpolate(frame, [delay, delay + 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        width: "100%",
        height: 1,
        background: `linear-gradient(90deg, transparent, ${COLORS.gold}, transparent)`,
        transform: `scaleX(${scaleX})`,
        margin: "16px 0",
      }}
    />
  );
};

export const Tag: React.FC<{ label: string; color?: string }> = ({
  label,
  color = COLORS.gold,
}) => (
  <span
    style={{
      display: "inline-block",
      border: `1px solid ${color}`,
      color,
      fontSize: 18,
      padding: "4px 14px",
      borderRadius: 4,
      letterSpacing: 2,
      fontFamily: '"Noto Sans JP", sans-serif',
    }}
  >
    {label}
  </span>
);
