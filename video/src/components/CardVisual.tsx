import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";

const SUIT_COLOR: Record<string, string> = {
  "♠": "#e0e0e0",
  "♥": "#e05050",
  "♦": "#e05050",
  "♣": "#e0e0e0",
};

export const PlayingCard: React.FC<{
  rank: string;
  suit: string;
  delay?: number;
  rotateDeg?: number;
  x?: number;
  y?: number;
}> = ({ rank, suit, delay = 0, rotateDeg = 0, x = 0, y = 0 }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [delay, delay + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const color = SUIT_COLOR[suit] ?? "#e0e0e0";

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: 80,
        height: 112,
        background: "#1a1820",
        border: `2px solid ${COLORS.goldDim}`,
        borderRadius: 8,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        transform: `rotate(${rotateDeg}deg) scale(${progress})`,
        opacity: progress,
        boxShadow: `0 4px 24px rgba(0,0,0,0.8), 0 0 8px ${COLORS.goldDim}40`,
      }}
    >
      <span style={{ color, fontSize: 22, fontWeight: "bold", lineHeight: 1 }}>{rank}</span>
      <span style={{ color, fontSize: 28, lineHeight: 1 }}>{suit}</span>
    </div>
  );
};

export const CardFan: React.FC<{ startDelay?: number }> = ({ startDelay = 0 }) => {
  const cards = [
    { rank: "A", suit: "♠", rotDeg: -20, x: 60, y: 30 },
    { rank: "K", suit: "♥", rotDeg: -8, x: 140, y: 10 },
    { rank: "Q", suit: "♦", rotDeg: 4, x: 220, y: 10 },
    { rank: "J", suit: "♣", rotDeg: 16, x: 300, y: 30 },
    { rank: "2", suit: "♠", rotDeg: 28, x: 370, y: 60 },
  ];
  return (
    <div style={{ position: "relative", width: 480, height: 180 }}>
      {cards.map((c, i) => (
        <PlayingCard
          key={i}
          rank={c.rank}
          suit={c.suit}
          rotateDeg={c.rotDeg}
          x={c.x}
          y={c.y}
          delay={startDelay + i * 6}
        />
      ))}
    </div>
  );
};
