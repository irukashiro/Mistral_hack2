import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 74–92s (2220–2760 frames) — localFrame  SETTING.md Logic State Manager
export const LogicScene: React.FC = () => {
  const frame = useCurrentFrame();

  const tactics = [
    {
      en: "ROLLER (ローラー)", ja: "ロラ作戦",
      trigger: "探偵CO ≥ 2人 → どちらかが偽物",
      desc: "「両方吊ることで確実に敵を処理する。今日AをAを、明日Bを吊る」",
      example: "Tactic_Available: Roller_Detective",
      color: COLORS.gold, delay: 16,
    },
    {
      en: "CONFIRMED WHITE", ja: "確定白（進行役）",
      trigger: "探偵CO = 1人（対抗なし） or ガード成功",
      desc: "「Cは唯一の探偵だから絶対味方。Cの指示に従って投票する」",
      example: "Confirmed_White: Player_C",
      color: "#60c0a0", delay: 56,
    },
    {
      en: "LINE CONFLICT", ja: "ライン考察",
      trigger: "探偵告発 ↔ 本人の主張が矛盾",
      desc: "「AとBのどちらかが嘘をついている。どちらかを吊るべきだ」",
      example: "Conflict_Line: [A, B]",
      color: "#6090e0", delay: 96,
    },
    {
      en: "ACTION CONTRADICTION", ja: "大富豪の矛盾",
      trigger: "「平民」主張 × 夜にジョーカー/2を連発",
      desc: "「平民にあんな強いカードはない。お前が富豪じゃないのか？」",
      example: "Action_Contradiction: {Target: C, Reason: too strong}",
      color: "#c08040", delay: 136,
    },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: `radial-gradient(ellipse at 40% 30%, #080c18 0%, ${COLORS.bg} 60%)`,
      display: "flex", flexDirection: "column", fontFamily: '"Noto Sans JP",sans-serif',
      padding: "24px 48px", boxSizing: "border-box",
    }}>
      <FadeIn delay={0} duration={12}>
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 10, color: "#6090e0", letterSpacing: 5, marginBottom: 5 }}>
            LOGIC STATE MANAGER — AI論理構築システム
          </div>
          <div style={{ fontSize: 22, color: COLORS.white, fontWeight: 700, marginBottom: 3 }}>
            人狼ロジックをAIに渡すフラグシステム
          </div>
          <div style={{ fontSize: 12, color: COLORS.dimWhite }}>
            Fact Logging → Logic Calculation → Tactic Flagging → NPC Speech Generation
          </div>
        </div>
      </FadeIn>

      <div style={{ display: "flex", gap: 16, flex: 1 }}>
        {/* Left: 2 tactics */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
          {tactics.slice(0, 2).map((t, i) => {
            const p = interpolate(frame, [t.delay, t.delay + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                background: COLORS.panel, border: `1px solid ${t.color}50`,
                borderRadius: 10, padding: "12px 16px", flex: 1,
                opacity: p, transform: `translateX(${(1 - p) * -16}px)`,
              }}>
                <div style={{ fontSize: 9, color: t.color, letterSpacing: 2, marginBottom: 3 }}>{t.en}</div>
                <div style={{ fontSize: 15, color: t.color, fontWeight: 700, marginBottom: 6 }}>{t.ja}</div>
                <div style={{ fontSize: 11, color: COLORS.dimWhite, marginBottom: 6 }}>
                  <span style={{ color: `${COLORS.dimWhite}80` }}>発動条件: </span>{t.trigger}
                </div>
                <div style={{ fontSize: 12, color: COLORS.white, fontStyle: "italic", marginBottom: 8, lineHeight: 1.55 }}>{t.desc}</div>
                <div style={{ fontFamily: '"Courier New",monospace', fontSize: 10, color: `${t.color}90`, background: "#0a0a10", borderRadius: 4, padding: "4px 8px" }}>
                  {t.example}
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: 2 tactics */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
          {tactics.slice(2).map((t, i) => {
            const p = interpolate(frame, [t.delay, t.delay + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                background: COLORS.panel, border: `1px solid ${t.color}50`,
                borderRadius: 10, padding: "12px 16px", flex: 1,
                opacity: p, transform: `translateX(${(1 - p) * 16}px)`,
              }}>
                <div style={{ fontSize: 9, color: t.color, letterSpacing: 2, marginBottom: 3 }}>{t.en}</div>
                <div style={{ fontSize: 15, color: t.color, fontWeight: 700, marginBottom: 6 }}>{t.ja}</div>
                <div style={{ fontSize: 11, color: COLORS.dimWhite, marginBottom: 6 }}>
                  <span style={{ color: `${COLORS.dimWhite}80` }}>発動条件: </span>{t.trigger}
                </div>
                <div style={{ fontSize: 12, color: COLORS.white, fontStyle: "italic", marginBottom: 8, lineHeight: 1.55 }}>{t.desc}</div>
                <div style={{ fontFamily: '"Courier New",monospace', fontSize: 10, color: `${t.color}90`, background: "#0a0a10", borderRadius: 4, padding: "4px 8px" }}>
                  {t.example}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <FadeIn delay={176} duration={14}>
        <div style={{
          marginTop: 12, padding: "10px 18px", background: "#0a0a14",
          border: `1px solid #4040a040`, borderRadius: 8,
          fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.7, textAlign: "center",
        }}>
          性格（Personality）とロジックが<span style={{ color: COLORS.gold }}>化学反応</span>してドラマを生む
          <span style={{ display: "block", fontSize: 10, color: `${COLORS.dimWhite}60` }}>
            Personality × Logic = emergent drama — no two games play the same.
          </span>
        </div>
      </FadeIn>
    </div>
  );
};
