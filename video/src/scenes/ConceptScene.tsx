import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 8–24s (240–720 frames) — localFrame
export const ConceptScene: React.FC = () => {
  const frame = useCurrentFrame();

  const pillars = [
    {
      en: "CARD GAME",
      ja: "大富豪",
      icon: "🃏",
      bullets: ["54-card deck with Jokers", "革命・8切り・シーケンス", "イカサマで格差を逆転"],
      color: COLORS.gold,
      delay: 18,
    },
    {
      en: "SOCIAL DEDUCTION",
      ja: "人狼",
      icon: "🐺",
      bullets: ["Discuss, Vote, Execute", "昼の議論で仲間を疑え", "NPCは自律的に動く"],
      color: "#d07040",
      delay: 38,
    },
    {
      en: "GENERATIVE AI",
      ja: "Mistral AI",
      icon: "✦",
      bullets: ["Unique world every play", "AIがキャラ・世界を生成", "手口と対策もAIが裁く"],
      color: "#6090e0",
      delay: 58,
    },
  ];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: COLORS.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: '"Noto Sans JP", sans-serif',
        padding: "0 56px",
        boxSizing: "border-box",
      }}
    >
      <FadeIn delay={0} duration={16}>
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <div style={{ fontSize: 11, color: COLORS.goldDim, letterSpacing: 5, marginBottom: 8 }}>
            CONCEPT
          </div>
          <div style={{ fontSize: 30, color: COLORS.white, fontWeight: 700, lineHeight: 1.4 }}>
            3つの要素が融合した
            <span style={{ color: COLORS.goldLight }}> 新感覚ゲーム</span>
          </div>
          <div style={{ fontSize: 14, color: COLORS.dimWhite, marginTop: 6 }}>
            A card game, social deduction, and generative AI — fused into one.
          </div>
        </div>
      </FadeIn>

      <div style={{ display: "flex", gap: 24, width: "100%", justifyContent: "center" }}>
        {pillars.map((p, i) => {
          const progress = interpolate(frame, [p.delay, p.delay + 22], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={i}
              style={{
                flex: 1,
                maxWidth: 300,
                background: COLORS.panel,
                border: `1px solid ${p.color}50`,
                borderRadius: 14,
                padding: "28px 22px",
                opacity: progress,
                transform: `translateY(${(1 - progress) * 28}px)`,
                boxShadow: `0 0 28px ${p.color}18`,
              }}
            >
              <div style={{ fontSize: 40, marginBottom: 10, textAlign: "center" }}>{p.icon}</div>
              <div style={{ fontSize: 11, color: `${p.color}90`, letterSpacing: 4, textAlign: "center", marginBottom: 4 }}>
                {p.en}
              </div>
              <div style={{ fontSize: 26, fontWeight: 900, color: p.color, textAlign: "center", marginBottom: 18 }}>
                {p.ja}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {p.bullets.map((b, j) => {
                  const bp = interpolate(
                    frame,
                    [p.delay + 20 + j * 12, p.delay + 36 + j * 12],
                    [0, 1],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                  );
                  return (
                    <div
                      key={j}
                      style={{ display: "flex", gap: 8, alignItems: "center", opacity: bp }}
                    >
                      <div
                        style={{
                          width: 4,
                          height: 4,
                          borderRadius: "50%",
                          background: p.color,
                          flexShrink: 0,
                        }}
                      />
                      <span style={{ fontSize: 13, color: COLORS.dimWhite }}>{b}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* AGENTS.md description — bottom */}
      <FadeIn delay={100} duration={20}>
        <div
          style={{
            marginTop: 28,
            padding: "14px 24px",
            background: "#0e0e14",
            border: `1px solid ${COLORS.goldDim}40`,
            borderRadius: 10,
            fontSize: 14,
            color: COLORS.dimWhite,
            textAlign: "center",
            lineHeight: 1.8,
            maxWidth: 700,
          }}
        >
          プレイヤーは<span style={{ color: COLORS.goldLight, fontWeight: 700 }}>記憶喪失の人物</span>として放り込まれ、
          AIが生成したNPCたちを<span style={{ color: COLORS.goldLight, fontWeight: 700 }}>論理と感情</span>で説き伏せて勝利を目指す
        </div>
      </FadeIn>
    </div>
  );
};
