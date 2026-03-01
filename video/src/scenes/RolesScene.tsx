import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 17–30s (510–900 frames) — localFrame  SETTING.md v4.0 2層構造
export const RolesScene: React.FC = () => {
  const frame = useCurrentFrame();

  const classes = [
    { en: "FUGO", ja: "富豪", icon: "👑", desc: "少数派。大富豪で勝ち逃げを狙う。\nFew cards win = escape the death game.", color: COLORS.gold, delay: 14 },
    { en: "HINMIN", ja: "貧民", icon: "⚡", desc: "少数派。イカサマで革命を起こせ。\nDecoys & cheats to overthrow the class.", color: "#d06060", delay: 26 },
    { en: "HEIMIN", ja: "平民 ×3", icon: "⚖", desc: "多数派。富豪と貧民を両方追放せよ。\nEliminate both minority factions.", color: "#a0a090", delay: 38 },
  ];

  const roles = [
    { en: "DETECTIVE", ja: "探偵", desc: "夜に1人の階級か手札を確認 / Peek one player's class or top card", color: "#60c0a0", delay: 68 },
    { en: "BODYGUARD", ja: "ボディガード", desc: "投票で1人の吊りを1度だけ無効化 / Block one execution per game", color: "#6080e0", delay: 82 },
    { en: "ACCOMPLICE", ja: "共犯者", desc: "平民だが敵陣営の勝利で自分も勝つ裏切者 / Wins with enemy faction", color: "#c06080", delay: 96 },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: `radial-gradient(ellipse at 30% 50%, #0e0c08 0%, ${COLORS.bg} 60%)`,
      display: "flex", fontFamily: '"Noto Sans JP",sans-serif',
      padding: "28px 48px", boxSizing: "border-box", gap: 32,
    }}>
      {/* Left: Classes */}
      <div style={{ flex: 1 }}>
        <FadeIn delay={0} duration={12}>
          <div style={{ fontSize: 10, color: COLORS.goldDim, letterSpacing: 4, marginBottom: 6 }}>CLASS — 階級</div>
          <div style={{ fontSize: 22, color: COLORS.white, fontWeight: 700, marginBottom: 16 }}>
            Three Factions / 三つ巴の構図
          </div>
        </FadeIn>
        {classes.map((c, i) => {
          const p = interpolate(frame, [c.delay, c.delay + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              display: "flex", gap: 12, padding: "10px 14px", marginBottom: 10,
              background: COLORS.panel, border: `1px solid ${c.color}45`,
              borderRadius: 10, opacity: p, transform: `translateX(${(1 - p) * -16}px)`,
            }}>
              <span style={{ fontSize: 24, flexShrink: 0 }}>{c.icon}</span>
              <div>
                <div style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 3 }}>
                  <span style={{ fontSize: 10, color: c.color, letterSpacing: 2 }}>{c.en}</span>
                  <span style={{ fontSize: 16, color: c.color, fontWeight: 700 }}>{c.ja}</span>
                </div>
                <div style={{ fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.65, whiteSpace: "pre-line" }}>{c.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Right: Roles (Special abilities) */}
      <div style={{ flex: 1 }}>
        <FadeIn delay={52} duration={12}>
          <div style={{ fontSize: 10, color: "#6080c0", letterSpacing: 4, marginBottom: 6 }}>ROLE — 役職（特殊能力）</div>
          <div style={{ fontSize: 22, color: COLORS.white, fontWeight: 700, marginBottom: 4 }}>
            Secret Abilities / 秘密の能力
          </div>
          <div style={{ fontSize: 12, color: COLORS.dimWhite, marginBottom: 14 }}>
            Assigned on top of class — mainly to HEIMIN
          </div>
        </FadeIn>
        {roles.map((r, i) => {
          const p = interpolate(frame, [r.delay, r.delay + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              padding: "10px 14px", marginBottom: 10,
              background: COLORS.panel, borderLeft: `3px solid ${r.color}`,
              borderRadius: "0 8px 8px 0", opacity: p, transform: `translateX(${(1 - p) * 16}px)`,
            }}>
              <div style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 3 }}>
                <span style={{ fontSize: 10, color: r.color, letterSpacing: 2 }}>{r.en}</span>
                <span style={{ fontSize: 14, color: r.color, fontWeight: 700 }}>{r.ja}</span>
              </div>
              <div style={{ fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.6 }}>{r.desc}</div>
            </div>
          );
        })}
        <FadeIn delay={120} duration={14}>
          <div style={{
            marginTop: 6, padding: "10px 14px", background: "#0a0a14",
            border: `1px solid #4040a040`, borderRadius: 8,
            fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.65,
          }}>
            <span style={{ color: COLORS.gold }}>True Win — 個人勝利条件</span>もAIが自動生成<br/>
            <span style={{ fontSize: 10, color: `${COLORS.dimWhite}70` }}>
              REVENGE / PROTECT / MARTYR / CLIMBER — determined per character
            </span>
          </div>
        </FadeIn>
      </div>
    </div>
  );
};
