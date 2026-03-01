import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 107–120s (3210–3600 frames) — localFrame
export const EndScene: React.FC = () => {
  const frame = useCurrentFrame();
  const glow = interpolate(frame, [0, 60, 140, 200, 390], [0.3, 1, 0.4, 0.9, 0.6], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const points = [
    { en: "Death game — 5 players, 3 factions", ja: "デスゲーム × 三つ巴の階級戦争" },
    { en: "Class + Role 2-layer system", ja: "階級×役職の2層構造" },
    { en: "Free-form AI-judged cheat duels", ja: "自由プロンプトのイカサマ対決" },
    { en: "Logic State Manager for NPC AI", ja: "人狼ロジックをNPCに渡すフラグシステム" },
    { en: "Generative AI — unique world every play", ja: "Mistral AIが毎回異なる世界・キャラを生成" },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: `radial-gradient(ellipse at 50% 50%, #1a1206 0%, ${COLORS.bg} 68%)`,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      fontFamily: '"Noto Sans JP",sans-serif', overflow: "hidden",
    }}>
      <div style={{
        position: "absolute", width: 700, height: 300,
        background: `radial-gradient(ellipse, ${COLORS.gold}1c 0%, transparent 68%)`, opacity: glow,
      }} />
      <FadeIn delay={0} duration={18}>
        <div style={{ fontSize: 52, fontWeight: 900, color: COLORS.goldLight, letterSpacing: 5,
          textAlign: "center", textShadow: `0 0 44px ${COLORS.gold}55`,
          fontFamily: '"Cinzel","Noto Serif JP",serif' }}>
          CLASS CONFLICT
        </div>
        <div style={{ fontSize: 30, color: COLORS.gold, letterSpacing: 13, textAlign: "center", marginBottom: 28 }}>
          MILLIONAIRE
        </div>
      </FadeIn>
      <div style={{ display: "flex", flexDirection: "column", gap: 9, alignItems: "flex-start", marginBottom: 28 }}>
        {points.map((p, i) => {
          const prog = interpolate(frame, [22 + i * 14, 38 + i * 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12, opacity: prog, transform: `translateY(${(1 - prog) * 8}px)` }}>
              <div style={{ width: 5, height: 5, borderRadius: "50%", background: COLORS.gold, boxShadow: `0 0 7px ${COLORS.gold}`, marginTop: 7, flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 13, color: COLORS.white, fontWeight: 700 }}>{p.ja}</div>
                <div style={{ fontSize: 11, color: COLORS.dimWhite }}>{p.en}</div>
              </div>
            </div>
          );
        })}
      </div>
      <FadeIn delay={106} duration={16} style={{ width: 460 }}>
        <div style={{ height: 1, background: `linear-gradient(90deg,transparent,${COLORS.gold},transparent)`, marginBottom: 16 }} />
      </FadeIn>
      <FadeIn delay={120} duration={18}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 11, color: COLORS.goldDim, letterSpacing: 4, marginBottom: 4 }}>POWERED BY</div>
          <div style={{ fontSize: 20, color: COLORS.gold, letterSpacing: 2, fontWeight: 700 }}>Mistral AI</div>
          <div style={{ fontSize: 12, color: COLORS.dimWhite, marginTop: 5, letterSpacing: 1 }}>Mistral AI Hackathon 2026</div>
        </div>
      </FadeIn>
    </div>
  );
};
