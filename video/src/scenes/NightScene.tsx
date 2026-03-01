import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";
import { CardFan } from "../components/CardVisual";

// 62–74s (1860–2220 frames) — localFrame  SETTING.md v4.0 夜パート+関係値
export const NightScene: React.FC = () => {
  const frame = useCurrentFrame();
  const revolutionGlow = interpolate(frame, [150, 175, 220], [0, 1, 0.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const matrix = [
    { from: "桐嶋→宮本", trust: 30, affinity: 70, delay: 30 },
    { from: "宮本→田中", trust: 80, affinity: 20, delay: 44 },
    { from: "田中→桐嶋", trust: 10, affinity: 60, delay: 58 },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: `radial-gradient(ellipse at 60% 40%, #060412 0%, ${COLORS.bg} 65%)`,
      display: "flex", fontFamily: '"Noto Sans JP",sans-serif',
      padding: "28px 48px", boxSizing: "border-box", gap: 36, alignItems: "center",
    }}>
      {/* Left: rules + matrix */}
      <div style={{ flex: 1 }}>
        <FadeIn delay={0} duration={12}>
          <div style={{ fontSize: 10, color: "#8060d0", letterSpacing: 4, marginBottom: 5 }}>PHASE 03 — NIGHT / 夜の大富豪</div>
          <div style={{ fontSize: 22, color: COLORS.white, fontWeight: 700, marginBottom: 12 }}>
            Cards + Relationships / カードと関係値
          </div>
        </FadeIn>

        {/* Relationship matrix */}
        <FadeIn delay={16} duration={12}>
          <div style={{ fontSize: 11, color: COLORS.goldDim, letterSpacing: 3, marginBottom: 10 }}>
            RELATIONSHIP MATRIX — Trust × Affinity (0–100)
          </div>
        </FadeIn>
        {matrix.map((m, i) => {
          const p = interpolate(frame, [m.delay, m.delay + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ marginBottom: 12, opacity: p, transform: `translateX(${(1 - p) * -14}px)` }}>
              <div style={{ fontSize: 12, color: COLORS.dimWhite, marginBottom: 5 }}>{m.from}</div>
              <div style={{ display: "flex", gap: 10 }}>
                {[
                  { label: "Trust", value: m.trust, color: "#6090e0" },
                  { label: "Affinity", value: m.affinity, color: "#e07060" },
                ].map((bar, j) => (
                  <div key={j} style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: bar.color, marginBottom: 3 }}>
                      <span>{bar.label}</span><span>{bar.value}</span>
                    </div>
                    <div style={{ background: "#1a1a20", borderRadius: 4, height: 5 }}>
                      <div style={{ background: bar.color, borderRadius: 4, height: 5, width: `${bar.value * p}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

        <FadeIn delay={80} duration={12}>
          <div style={{ padding: "9px 14px", background: "#0e0e14", border: `1px solid ${COLORS.goldDim}40`, borderRadius: 8, fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.7 }}>
            NPCはAffinityが高い相手へパスを回し、<br/>
            低い相手には強いカードで妨害する
            <span style={{ display: "block", fontSize: 10, color: `${COLORS.dimWhite}60` }}>
              NPCs play cards based on Trust × Affinity — like real humans.
            </span>
          </div>
        </FadeIn>
      </div>

      {/* Right: card + revolution */}
      <div style={{ flex: 0.85, display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
        <FadeIn delay={10} duration={16}><CardFan startDelay={12} /></FadeIn>
        <div style={{
          opacity: revolutionGlow, border: `2px solid #7050c0`, borderRadius: 12,
          padding: "14px 36px", textAlign: "center",
          background: `radial-gradient(ellipse, #30148050 0%, transparent 70%)`,
          transform: `scale(${0.88 + revolutionGlow * 0.12})`,
        }}>
          <div style={{ fontSize: 9, color: "#a080e0", letterSpacing: 5, marginBottom: 3 }}>REVOLUTION</div>
          <div style={{ fontSize: 26, color: "#c0a0ff", fontWeight: 900 }}>革命発動！</div>
          <div style={{ fontSize: 11, color: COLORS.dimWhite, marginTop: 3 }}>Quad played — strength reversed</div>
        </div>
      </div>
    </div>
  );
};
