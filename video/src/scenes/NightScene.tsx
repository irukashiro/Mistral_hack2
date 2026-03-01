import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";
import { CardFan } from "../components/CardVisual";

// 76–98s (2280–2940 frames) — localFrame
export const NightScene: React.FC = () => {
  const frame = useCurrentFrame();

  const revolutionGlow = interpolate(frame, [180, 210, 270], [0, 1, 0.35], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const rules = [
    { icon: "♠", en: "Strength: 3 (low) → 2 (high)", ja: "スート: ♠>♥>♦>♣", delay: 18 },
    { icon: "✂", en: "8-Cut — resets the table", ja: "8切り: 8を出すと場をリセット", delay: 36 },
    { icon: "🔄", en: "Revolution — strength reversed", ja: "革命: クアッドで強弱逆転", delay: 54 },
    { icon: "🃏", en: "Sequence — same-suit 3+ chain", ja: "シーケンス: 同スート3枚以上", delay: 72 },
    { icon: "🏆", en: "3 clears → next day begins", ja: "3回流れたら翌日へ", delay: 90 },
  ];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: `radial-gradient(ellipse at 60% 40%, #060412 0%, ${COLORS.bg} 65%)`,
        display: "flex",
        fontFamily: '"Noto Sans JP", sans-serif',
        padding: "36px 52px",
        boxSizing: "border-box",
        gap: 44,
        alignItems: "center",
      }}
    >
      {/* Left: rules */}
      <div style={{ flex: 1 }}>
        <FadeIn delay={0} duration={16}>
          <div style={{ fontSize: 10, color: "#8060d0", letterSpacing: 5, marginBottom: 8 }}>
            PHASE 03 — NIGHT / 夜の大富豪
          </div>
          <div style={{ fontSize: 28, color: COLORS.white, fontWeight: 700, marginBottom: 4 }}>
            全員でカードを戦わせろ
          </div>
          <div style={{ fontSize: 13, color: COLORS.dimWhite, marginBottom: 24 }}>
            Everyone competes at the card table.
          </div>
        </FadeIn>

        {rules.map((r, i) => {
          const p = interpolate(frame, [r.delay, r.delay + 18], [0, 1], {
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
                marginBottom: 13,
                opacity: p,
                transform: `translateX(${(1 - p) * -18}px)`,
              }}
            >
              <span
                style={{
                  fontSize: 16,
                  color: COLORS.gold,
                  width: 20,
                  textAlign: "center",
                  flexShrink: 0,
                }}
              >
                {r.icon}
              </span>
              <div>
                <div style={{ fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.3 }}>{r.en}</div>
                <div style={{ fontSize: 13, color: COLORS.white, fontWeight: 600 }}>{r.ja}</div>
              </div>
            </div>
          );
        })}

        <FadeIn delay={115} duration={18}>
          <div
            style={{
              marginTop: 10,
              padding: "10px 14px",
              background: "#0e0e14",
              border: `1px solid ${COLORS.goldDim}40`,
              borderRadius: 8,
              fontSize: 12,
              color: COLORS.dimWhite,
              lineHeight: 1.7,
            }}
          >
            NPCは <span style={{ color: COLORS.gold }}>勝利条件</span> を意識しながら<br />
            カードプレイを自律的に選択する
            <span style={{ color: `${COLORS.dimWhite}60`, fontSize: 11, display: "block" }}>
              NPCs choose plays based on their secret mission.
            </span>
          </div>
        </FadeIn>
      </div>

      {/* Right: visuals */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 28,
        }}
      >
        <FadeIn delay={12} duration={20}>
          <CardFan startDelay={16} />
        </FadeIn>

        {/* Revolution banner */}
        <div
          style={{
            opacity: revolutionGlow,
            background: `radial-gradient(ellipse, #30148060 0%, transparent 70%)`,
            border: `2px solid #7050c0`,
            borderRadius: 14,
            padding: "16px 40px",
            textAlign: "center",
            transform: `scale(${0.88 + revolutionGlow * 0.12})`,
            boxShadow: `0 0 40px #6040c040`,
          }}
        >
          <div style={{ fontSize: 9, color: "#a080e0", letterSpacing: 5, marginBottom: 4 }}>
            REVOLUTION
          </div>
          <div style={{ fontSize: 28, color: "#c0a0ff", fontWeight: 900 }}>
            革命発動！
          </div>
          <div style={{ fontSize: 12, color: COLORS.dimWhite, marginTop: 4 }}>
            Quad played — strength order reversed
          </div>
        </div>

        {/* Joker badge */}
        <FadeIn delay={260} duration={18}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 20px",
              background: COLORS.panel,
              border: `1px solid ${COLORS.goldDim}60`,
              borderRadius: 8,
            }}
          >
            <span style={{ fontSize: 24 }}>🃏</span>
            <div>
              <div style={{ fontSize: 13, color: COLORS.gold, fontWeight: 700 }}>JOKER</div>
              <div style={{ fontSize: 11, color: COLORS.dimWhite }}>
                ワイルドカード兼最強 · Wildcard & strongest
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </div>
  );
};
