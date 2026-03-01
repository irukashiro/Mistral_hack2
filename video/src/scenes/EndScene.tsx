import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 113–120s (3390–3600 frames) — localFrame
export const EndScene: React.FC = () => {
  const frame = useCurrentFrame();

  const glowPulse = interpolate(
    frame,
    [0, 55, 110, 170, 210],
    [0.3, 1, 0.45, 0.9, 0.6],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const points = [
    { en: "Card game × Social deduction × Generative AI", ja: "3要素が融合した新感覚ゲーム" },
    { en: "AI generates a unique world every playthrough", ja: "Mistral AIが毎回異なる世界を生成" },
    { en: "Free-form cheat duels judged by AI", ja: "自由プロンプトのイカサマ対決" },
    { en: "Lite mode — 5 players, quick setup", ja: "Liteモード: 5人・即プレイ対応" },
  ];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: `radial-gradient(ellipse at 50% 50%, #1a1206 0%, ${COLORS.bg} 68%)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: '"Noto Sans JP", sans-serif',
        overflow: "hidden",
      }}
    >
      {/* Glow */}
      <div
        style={{
          position: "absolute",
          width: 720,
          height: 320,
          background: `radial-gradient(ellipse, ${COLORS.gold}1e 0%, transparent 68%)`,
          opacity: glowPulse,
        }}
      />

      {/* Title */}
      <FadeIn delay={0} duration={22}>
        <div
          style={{
            fontSize: 58,
            fontWeight: 900,
            color: COLORS.goldLight,
            letterSpacing: 6,
            textAlign: "center",
            textShadow: `0 0 48px ${COLORS.gold}55`,
            fontFamily: '"Cinzel", "Noto Serif JP", serif',
          }}
        >
          CLASS CONFLICT
        </div>
        <div
          style={{
            fontSize: 34,
            color: COLORS.gold,
            letterSpacing: 14,
            textAlign: "center",
            marginBottom: 32,
          }}
        >
          MILLIONAIRE
        </div>
      </FadeIn>

      {/* Points */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 11,
          alignItems: "flex-start",
          marginBottom: 32,
        }}
      >
        {points.map((p, i) => {
          const prog = interpolate(frame, [26 + i * 16, 44 + i * 16], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 14,
                opacity: prog,
                transform: `translateY(${(1 - prog) * 10}px)`,
              }}
            >
              <div
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: COLORS.gold,
                  boxShadow: `0 0 8px ${COLORS.gold}`,
                  marginTop: 6,
                  flexShrink: 0,
                }}
              />
              <div>
                <div style={{ fontSize: 14, color: COLORS.white, fontWeight: 700 }}>{p.ja}</div>
                <div style={{ fontSize: 11, color: COLORS.dimWhite, marginTop: 1 }}>{p.en}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Divider */}
      <FadeIn delay={100} duration={18} style={{ width: 480 }}>
        <div
          style={{
            height: 1,
            background: `linear-gradient(90deg, transparent, ${COLORS.gold}, transparent)`,
            marginBottom: 18,
          }}
        />
      </FadeIn>

      <FadeIn delay={115} duration={20}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 13, color: COLORS.goldDim, letterSpacing: 4, marginBottom: 4 }}>
            POWERED BY
          </div>
          <div style={{ fontSize: 18, color: COLORS.gold, letterSpacing: 2, fontWeight: 700 }}>
            Mistral AI
          </div>
          <div style={{ fontSize: 12, color: COLORS.dimWhite, marginTop: 6, letterSpacing: 1 }}>
            Mistral AI Hackathon 2026
          </div>
        </div>
      </FadeIn>
    </div>
  );
};
