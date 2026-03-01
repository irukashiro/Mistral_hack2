import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 0–5s (0–150 frames)
export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const glow = interpolate(frame, [0, 40, 100, 150], [0, 1, 0.5, 0.8], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  return (
    <div style={{
      width: "100%", height: "100%",
      background: `radial-gradient(ellipse at 50% 55%, #1e1508 0%, #0a0a0f 65%)`,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      fontFamily: '"Cinzel","Noto Serif JP",serif', overflow: "hidden",
    }}>
      <div style={{
        position: "absolute", width: 700, height: 220,
        background: `radial-gradient(ellipse, ${COLORS.gold}25 0%, transparent 68%)`,
        opacity: glow,
      }} />
      <FadeIn delay={5} duration={18}>
        <div style={{ fontSize: 10, color: COLORS.goldDim, letterSpacing: 5, marginBottom: 16, fontFamily: '"Noto Sans JP",sans-serif' }}>
          MISTRAL AI HACKATHON 2026
        </div>
      </FadeIn>
      <FadeIn delay={16} duration={20}>
        <div style={{ fontSize: 72, fontWeight: 900, color: COLORS.goldLight, letterSpacing: 6,
          textShadow: `0 0 50px ${COLORS.gold}70`, textAlign: "center", lineHeight: 1.05 }}>
          CLASS CONFLICT
        </div>
      </FadeIn>
      <FadeIn delay={30} duration={18}>
        <div style={{ fontSize: 42, color: COLORS.gold, letterSpacing: 15, textAlign: "center", marginTop: 2 }}>
          MILLIONAIRE
        </div>
      </FadeIn>
      <FadeIn delay={48} duration={14} style={{ width: 520, marginTop: 14 }}>
        <div style={{ height: 1, background: `linear-gradient(90deg,transparent,${COLORS.gold},transparent)` }} />
      </FadeIn>
      <FadeIn delay={62} duration={16}>
        <div style={{ display: "flex", gap: 14, alignItems: "center", marginTop: 14 }}>
          {["大富豪","×","人狼","×","AI生成キャラクター"].map((t, i) => (
            <span key={i} style={{
              fontSize: t === "×" ? 18 : 22, fontFamily: '"Noto Sans JP",sans-serif',
              color: t === "×" ? COLORS.goldDim : COLORS.dimWhite,
              letterSpacing: t === "×" ? 0 : 3, fontWeight: t === "×" ? 400 : 700,
            }}>{t}</span>
          ))}
        </div>
      </FadeIn>
      <FadeIn delay={90} duration={16}>
        <div style={{ marginTop: 18, fontSize: 13, color: COLORS.dimWhite, textAlign: "center",
          lineHeight: 1.8, fontFamily: '"Noto Sans JP",sans-serif' }}>
          AI-Driven Hidden Identity Adventure Card Game<br/>
          <span style={{ color: COLORS.goldDim, fontSize: 11 }}>正体隠匿アドベンチャーカードゲーム</span>
        </div>
      </FadeIn>
    </div>
  );
};
