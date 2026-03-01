import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 98–113s (2940–3390 frames) — localFrame
export const AIScene: React.FC = () => {
  const frame = useCurrentFrame();

  const features = [
    {
      model: "mistral-large",
      en: "Character Generation",
      ja: "キャラクター生成",
      desc: "人物像・バックストーリー・隠れた目標をAIが毎回生成",
      color: COLORS.gold,
      delay: 16,
    },
    {
      model: "mistral-large",
      en: "Cheat Judgment",
      ja: "イカサマ審判",
      desc: "手口と対策を文脈込みで3段階判定",
      color: COLORS.gold,
      delay: 32,
    },
    {
      model: "mistral-small",
      en: "NPC Speech",
      ja: "NPC発言生成",
      desc: "議論スタイル・関係性・勝利条件を踏まえた戦略的発言",
      color: "#6090e0",
      delay: 48,
    },
    {
      model: "mistral-small",
      en: "NPC Voting",
      ja: "NPC投票判断",
      desc: "会話履歴と個人目標から自律的に投票先を決定",
      color: "#6090e0",
      delay: 64,
    },
    {
      model: "mistral-small",
      en: "Detective Report",
      ja: "探偵調査結果",
      desc: "証拠・役職・関係性から推論した調査レポートを生成",
      color: "#60c0a0",
      delay: 80,
    },
    {
      model: "mistral-small",
      en: "Night Atmosphere",
      ja: "夜の状況描写",
      desc: "没入感を高める雰囲気テキストを毎夜生成",
      color: "#8060a0",
      delay: 96,
    },
  ];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: `radial-gradient(ellipse at 40% 50%, #080c18 0%, ${COLORS.bg} 65%)`,
        display: "flex",
        fontFamily: '"Noto Sans JP", sans-serif',
        padding: "32px 52px",
        boxSizing: "border-box",
        gap: 36,
      }}
    >
      {/* Left: feature list */}
      <div style={{ flex: 1.1 }}>
        <FadeIn delay={0} duration={16}>
          <div style={{ marginBottom: 22 }}>
            <div style={{ fontSize: 10, color: "#6090e0", letterSpacing: 5, marginBottom: 6 }}>
              AI INTEGRATION — Mistral AI
            </div>
            <div style={{ fontSize: 28, color: COLORS.white, fontWeight: 700, marginBottom: 4 }}>
              すべてがAIで生成される
            </div>
            <div style={{ fontSize: 13, color: COLORS.dimWhite }}>
              Every play, a completely different world.
            </div>
          </div>
        </FadeIn>

        {features.map((f, i) => {
          const p = interpolate(frame, [f.delay, f.delay + 16], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "9px 14px",
                background: COLORS.panel,
                borderLeft: `3px solid ${f.color}`,
                borderRadius: "0 8px 8px 0",
                marginBottom: 8,
                opacity: p,
                transform: `translateX(${(1 - p) * -20}px)`,
              }}
            >
              <div
                style={{
                  fontSize: 9,
                  color: f.color,
                  letterSpacing: 0.5,
                  minWidth: 106,
                  fontFamily: '"Courier New", monospace',
                  lineHeight: 1.4,
                }}
              >
                {f.model}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 2 }}>
                  <span style={{ fontSize: 11, color: f.color, letterSpacing: 0.5 }}>{f.en}</span>
                  <span style={{ fontSize: 13, color: COLORS.white, fontWeight: 700 }}>{f.ja}</span>
                </div>
                <div style={{ fontSize: 11, color: COLORS.dimWhite }}>{f.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Right: sample cards */}
      <div
        style={{
          flex: 0.75,
          display: "flex",
          flexDirection: "column",
          gap: 14,
          justifyContent: "center",
        }}
      >
        {/* Generated character sample */}
        <FadeIn delay={28} duration={20}>
          <div
            style={{
              background: COLORS.panel,
              border: `1px solid ${COLORS.goldDim}`,
              borderRadius: 10,
              padding: "16px 18px",
            }}
          >
            <div style={{ fontSize: 9, color: COLORS.goldDim, letterSpacing: 3, marginBottom: 8 }}>
              AI-GENERATED CHARACTER
            </div>
            <div style={{ fontSize: 14, color: COLORS.gold, fontWeight: 700, marginBottom: 6 }}>
              桐嶋 源治 · <span style={{ fontSize: 11 }}>FUGO</span>
            </div>
            <div style={{ fontSize: 11, color: COLORS.dimWhite, lineHeight: 1.7 }}>
              廃病院の元院長。過去の医療事故を隠蔽するため、
              この夜会に参加した。田中とは10年来の共犯関係。
            </div>
            <div style={{ marginTop: 8, fontSize: 10, color: "#c06060", letterSpacing: 1 }}>
              SECRET MISSION — 田中を処刑から守れ
            </div>
          </div>
        </FadeIn>

        {/* NPC speech sample */}
        <FadeIn delay={90} duration={20}>
          <div
            style={{
              background: COLORS.panel,
              border: `1px solid #203060`,
              borderRadius: 10,
              padding: "16px 18px",
            }}
          >
            <div style={{ fontSize: 9, color: "#4060a0", letterSpacing: 3, marginBottom: 8 }}>
              AI-GENERATED NPC SPEECH
            </div>
            <div style={{ fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.75, fontStyle: "italic" }}>
              「あなたの記憶がないのは都合がよすぎる。
              昨夜のカードの流れ、貧民なら絶対に気づいていたはず——
              宮本、同意するか？」
            </div>
          </div>
        </FadeIn>

        {/* Victory badge */}
        <FadeIn delay={140} duration={18}>
          <div
            style={{
              background: "#0a0a14",
              border: `1px solid #4040a060`,
              borderRadius: 10,
              padding: "14px 18px",
            }}
          >
            <div style={{ fontSize: 9, color: "#6060c0", letterSpacing: 3, marginBottom: 8 }}>
              SECRET MISSION EXAMPLE — 個人勝利条件
            </div>
            {[
              { type: "REVENGE", ja: "復讐者", desc: "ターゲットが処刑される" },
              { type: "MARTYR", ja: "殉教者", desc: "自分自身が処刑される" },
              { type: "PROTECT", ja: "庇護者", desc: "ターゲットが最初に上がる" },
            ].map((v, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: 8,
                  marginBottom: 5,
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: 10, color: "#8080c0", minWidth: 56, letterSpacing: 0.5 }}>
                  {v.type}
                </span>
                <span style={{ fontSize: 12, color: COLORS.white, minWidth: 48 }}>{v.ja}</span>
                <span style={{ fontSize: 11, color: COLORS.dimWhite }}>{v.desc}</span>
              </div>
            ))}
          </div>
        </FadeIn>
      </div>
    </div>
  );
};
