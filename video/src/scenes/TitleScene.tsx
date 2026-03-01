import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 0–8s (0–240 frames)
export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();

  const glowOpacity = interpolate(
    frame,
    [0, 60, 130, 200, 240],
    [0, 0.8, 0.4, 1, 0.7],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const particleOpacity = interpolate(frame, [60, 120], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: `radial-gradient(ellipse at 50% 55%, #1e1508 0%, #0a0a0f 65%)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: '"Cinzel", "Noto Serif JP", serif',
        overflow: "hidden",
      }}
    >
      {/* Ambient glow */}
      <div
        style={{
          position: "absolute",
          width: 800,
          height: 260,
          background: `radial-gradient(ellipse, ${COLORS.gold}28 0%, transparent 68%)`,
          opacity: glowOpacity,
        }}
      />

      {/* Particle dots */}
      {[...Array(12)].map((_, i) => {
        const x = 80 + (i % 6) * 200;
        const y = 80 + Math.floor(i / 6) * 520;
        const delay = 60 + i * 8;
        const op = interpolate(frame, [delay, delay + 20], [0, 0.4], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: 2,
              height: 2,
              borderRadius: "50%",
              background: COLORS.gold,
              opacity: op * particleOpacity,
            }}
          />
        );
      })}

      {/* Hackathon tag */}
      <FadeIn delay={5} duration={20}>
        <div
          style={{
            fontSize: 11,
            color: COLORS.goldDim,
            letterSpacing: 5,
            marginBottom: 20,
            fontFamily: '"Noto Sans JP", sans-serif',
          }}
        >
          MISTRAL AI HACKATHON 2026
        </div>
      </FadeIn>

      {/* Main title */}
      <FadeIn delay={18} duration={28}>
        <div
          style={{
            fontSize: 76,
            fontWeight: 900,
            color: COLORS.goldLight,
            letterSpacing: 7,
            textShadow: `0 0 50px ${COLORS.gold}70, 0 2px 0 #000`,
            textAlign: "center",
            lineHeight: 1.05,
          }}
        >
          CLASS CONFLICT
        </div>
      </FadeIn>

      <FadeIn delay={36} duration={22}>
        <div
          style={{
            fontSize: 46,
            color: COLORS.gold,
            letterSpacing: 16,
            textAlign: "center",
            marginTop: 2,
          }}
        >
          MILLIONAIRE
        </div>
      </FadeIn>

      {/* Divider */}
      <FadeIn delay={60} duration={18} style={{ width: 560, marginTop: 18 }}>
        <div
          style={{
            width: "100%",
            height: 1,
            background: `linear-gradient(90deg, transparent, ${COLORS.gold}, transparent)`,
          }}
        />
      </FadeIn>

      {/* Tagline — three pillars */}
      <FadeIn delay={78} duration={22}>
        <div
          style={{
            display: "flex",
            gap: 16,
            alignItems: "center",
            marginTop: 18,
          }}
        >
          {["大富豪", "×", "人狼", "×", "AI"].map((t, i) => (
            <span
              key={i}
              style={{
                fontSize: t === "×" ? 20 : 26,
                color: t === "×" ? COLORS.goldDim : COLORS.dimWhite,
                letterSpacing: t === "×" ? 0 : 4,
                fontFamily: '"Noto Sans JP", sans-serif',
                fontWeight: t === "×" ? 400 : 700,
              }}
            >
              {t}
            </span>
          ))}
        </div>
      </FadeIn>

      {/* Subtitle — from AGENTS.md */}
      <FadeIn delay={115} duration={22}>
        <div
          style={{
            marginTop: 22,
            fontSize: 14,
            color: COLORS.dimWhite,
            textAlign: "center",
            lineHeight: 1.9,
            fontFamily: '"Noto Sans JP", sans-serif',
            maxWidth: 560,
          }}
        >
          AI駆動型・正体隠匿アドベンチャーカードゲーム<br />
          <span style={{ color: COLORS.goldDim, fontSize: 12 }}>
            AI-Driven Hidden Identity Adventure Card Game
          </span>
        </div>
      </FadeIn>
    </div>
  );
};
