import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 92–107s (2760–3210 frames) — localFrame
export const AIScene: React.FC = () => {
  const frame = useCurrentFrame();

  const features = [
    { model: "mistral-large", en: "Character Generation", ja: "キャラ生成", desc: "世界設定・人物像・因縁をゼロから生成", color: COLORS.gold, delay: 14 },
    { model: "mistral-large", en: "Cheat Judgment", ja: "イカサマ審判", desc: "陽動と対策を文脈込みで3段階判定", color: COLORS.gold, delay: 26 },
    { model: "mistral-small", en: "NPC Speech", ja: "NPC発言", desc: "性格・関係値・勝利条件を踏まえた戦略発言", color: "#6090e0", delay: 38 },
    { model: "mistral-small", en: "NPC Vote", ja: "NPC投票", desc: "Trustスコアとロジックフラグから自律的に決定", color: "#6090e0", delay: 50 },
    { model: "mistral-small", en: "Detective Report", ja: "探偵調査", desc: "証拠・関係性から推論した調査レポートを生成", color: "#60c0a0", delay: 62 },
    { model: "mistral-small", en: "Night Atmosphere", ja: "夜の描写", desc: "没入感を高める雰囲気テキストを毎夜生成", color: "#8060a0", delay: 74 },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: `radial-gradient(ellipse at 40% 50%, #080c18 0%, ${COLORS.bg} 65%)`,
      display: "flex", fontFamily: '"Noto Sans JP",sans-serif',
      padding: "24px 48px", boxSizing: "border-box", gap: 30,
    }}>
      <div style={{ flex: 1.1 }}>
        <FadeIn delay={0} duration={12}>
          <div style={{ marginBottom: 18 }}>
            <div style={{ fontSize: 10, color: "#6090e0", letterSpacing: 5, marginBottom: 5 }}>AI INTEGRATION — Mistral AI</div>
            <div style={{ fontSize: 24, color: COLORS.white, fontWeight: 700, marginBottom: 3 }}>すべてがAIで生成される</div>
            <div style={{ fontSize: 12, color: COLORS.dimWhite }}>Every play, a completely different world and cast.</div>
          </div>
        </FadeIn>
        {features.map((f, i) => {
          const p = interpolate(frame, [f.delay, f.delay + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 12,
              padding: "8px 12px", background: COLORS.panel,
              borderLeft: `3px solid ${f.color}`, borderRadius: "0 7px 7px 0",
              marginBottom: 7, opacity: p, transform: `translateX(${(1 - p) * -18}px)`,
            }}>
              <div style={{ fontSize: 8, color: f.color, minWidth: 100, fontFamily: '"Courier New",monospace', lineHeight: 1.4 }}>{f.model}</div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", gap: 7, alignItems: "baseline", marginBottom: 1 }}>
                  <span style={{ fontSize: 10, color: f.color, letterSpacing: 0.5 }}>{f.en}</span>
                  <span style={{ fontSize: 13, color: COLORS.white, fontWeight: 700 }}>{f.ja}</span>
                </div>
                <div style={{ fontSize: 11, color: COLORS.dimWhite }}>{f.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ flex: 0.7, display: "flex", flexDirection: "column", gap: 12, justifyContent: "center" }}>
        <FadeIn delay={24} duration={14}>
          <div style={{ background: COLORS.panel, border: `1px solid ${COLORS.goldDim}`, borderRadius: 10, padding: "14px 16px" }}>
            <div style={{ fontSize: 9, color: COLORS.goldDim, letterSpacing: 3, marginBottom: 7 }}>AI-GENERATED CHARACTER</div>
            <div style={{ fontSize: 13, color: COLORS.gold, fontWeight: 700, marginBottom: 5 }}>桐嶋 源治 · FUGO</div>
            <div style={{ fontSize: 11, color: COLORS.dimWhite, lineHeight: 1.7 }}>
              廃病院の元院長。医療事故を隠蔽するため参加。田中とは10年来の共犯関係。
            </div>
            <div style={{ marginTop: 7, fontSize: 10, color: "#c06060" }}>TRUE WIN — 田中を処刑から守れ</div>
          </div>
        </FadeIn>
        <FadeIn delay={88} duration={14}>
          <div style={{ background: COLORS.panel, border: `1px solid #203060`, borderRadius: 10, padding: "14px 16px" }}>
            <div style={{ fontSize: 9, color: "#4060a0", letterSpacing: 3, marginBottom: 7 }}>AI-GENERATED NPC SPEECH</div>
            <div style={{ fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.75, fontStyle: "italic" }}>
              「平民だと言っているが、昨夜ジョーカーを出したな？それが平民の手札か？」
            </div>
          </div>
        </FadeIn>
        <FadeIn delay={140} duration={14}>
          <div style={{ background: "#0a0a14", border: `1px solid #4040a040`, borderRadius: 10, padding: "12px 16px" }}>
            <div style={{ fontSize: 9, color: "#6060c0", letterSpacing: 3, marginBottom: 7 }}>RESULT SCREEN — リザルト全真相開示</div>
            {["全員の真の階級", "AIが生成した因縁相関図", "個人勝利条件の達成状況", "伏線回収アハ体験"].map((s, i) => (
              <div key={i} style={{ display: "flex", gap: 7, marginBottom: 4, alignItems: "center" }}>
                <div style={{ width: 4, height: 4, borderRadius: "50%", background: COLORS.gold, flexShrink: 0 }} />
                <span style={{ fontSize: 11, color: COLORS.dimWhite }}>{s}</span>
              </div>
            ))}
          </div>
        </FadeIn>
      </div>
    </div>
  );
};
