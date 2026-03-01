import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 30–47s (900–1410 frames) — localFrame  SETTING.md v3.0/v4.0
export const DayScene: React.FC = () => {
  const frame = useCurrentFrame();

  const personalities = [
    { en: "LOGICAL", ja: "論理型", desc: "証拠を絶対視。Trustを最優先に投票。\nFollows evidence — even over friends.", color: "#60a0e0", delay: 20 },
    { en: "EMOTIONAL", ja: "感情型", desc: "Affinityが高い相手を守る。ロジックより感情。\nDefends allies regardless of evidence.", color: "#e07060", delay: 34 },
    { en: "PASSIVE", ja: "ヘイト回避型", desc: "多数派意見に便乗。自ら動かない。\nAlways follows the majority vote.", color: "#a0a090", delay: 48 },
    { en: "CHAOTIC", ja: "破滅型", desc: "ロジックを無視し場を支配しようとする。\nIgnores logic; disrupts everything.", color: "#c060c0", delay: 62 },
  ];

  const voteAnim = interpolate(frame, [100, 128], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const execAnim = interpolate(frame, [148, 165], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{
      width: "100%", height: "100%",
      background: `radial-gradient(ellipse at 35% 40%, #0e0c08 0%, ${COLORS.bg} 60%)`,
      display: "flex", fontFamily: '"Noto Sans JP",sans-serif',
      padding: "28px 48px", boxSizing: "border-box", gap: 32,
    }}>
      {/* Left: Personality types */}
      <div style={{ flex: 1.1 }}>
        <FadeIn delay={0} duration={12}>
          <div style={{ fontSize: 10, color: COLORS.goldDim, letterSpacing: 4, marginBottom: 5 }}>PHASE 01 — DAY / 昼の会議</div>
          <div style={{ fontSize: 24, color: COLORS.white, fontWeight: 700, marginBottom: 4 }}>
            NPCの思考 — Personality Types
          </div>
          <div style={{ fontSize: 12, color: COLORS.dimWhite, marginBottom: 16 }}>
            Each NPC has Trust × Affinity parameters and a personality that governs their vote.
          </div>
        </FadeIn>
        {personalities.map((p, i) => {
          const prog = interpolate(frame, [p.delay, p.delay + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              display: "flex", gap: 12, padding: "9px 12px", marginBottom: 9,
              background: COLORS.panel, borderLeft: `3px solid ${p.color}`,
              borderRadius: "0 8px 8px 0", opacity: prog, transform: `translateX(${(1 - prog) * -14}px)`,
            }}>
              <div>
                <div style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 3 }}>
                  <span style={{ fontSize: 10, color: p.color, letterSpacing: 2, minWidth: 68 }}>{p.en}</span>
                  <span style={{ fontSize: 14, color: p.color, fontWeight: 700 }}>{p.ja}</span>
                </div>
                <div style={{ fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.6, whiteSpace: "pre-line" }}>{p.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Right: Vote + Execution */}
      <div style={{ flex: 0.85, display: "flex", flexDirection: "column", gap: 12 }}>
        <FadeIn delay={88} duration={14}>
          <div style={{ background: COLORS.panel, border: `1px solid ${COLORS.goldDim}`, borderRadius: 10, padding: "16px 18px" }}>
            <div style={{ fontSize: 10, color: COLORS.goldDim, letterSpacing: 4, marginBottom: 12 }}>VOTE TALLY — 投票</div>
            {[
              { name: "桐嶋 源治", tag: "FUGO", votes: 3, color: COLORS.gold },
              { name: "宮本 沙也", tag: "HINMIN", votes: 1, color: "#d06060" },
              { name: "田中 一郎", tag: "DETECTIVE", votes: 0, color: "#60c0a0" },
            ].map((v, i) => (
              <div key={i} style={{ marginBottom: 11 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 13, color: v.color }}>{v.name} <span style={{ fontSize: 9, opacity: 0.7 }}>[{v.tag}]</span></span>
                  <span style={{ fontSize: 12, color: v.color }}>{v.votes}票</span>
                </div>
                <div style={{ background: "#1a1a20", borderRadius: 4, height: 5 }}>
                  <div style={{ background: v.color, borderRadius: 4, height: 5, width: `${(v.votes / 4) * 100 * voteAnim}%` }} />
                </div>
              </div>
            ))}
          </div>
        </FadeIn>

        <div style={{ opacity: execAnim, transform: `scale(${0.94 + execAnim * 0.06})` }}>
          <div style={{ background: "#200808", border: "1.5px solid #802020", borderRadius: 10, padding: "14px 18px", textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "#ff6060", letterSpacing: 4, marginBottom: 6 }}>EXECUTED — 処刑</div>
            <div style={{ fontSize: 20, color: COLORS.white, fontWeight: 700 }}>桐嶋 源治</div>
            <div style={{ fontSize: 11, color: COLORS.dimWhite, marginTop: 4 }}>最多票 · Most votes received</div>
          </div>
        </div>

        <FadeIn delay={172} duration={14}>
          <div style={{ padding: "10px 14px", background: "#0a0a14", border: `1px solid #4040a040`, borderRadius: 8, fontSize: 12, color: COLORS.dimWhite, lineHeight: 1.7 }}>
            処刑後 → <span style={{ color: "#8080e0" }}>True Win即時チェック</span><br/>
            <span style={{ fontSize: 10, color: `${COLORS.dimWhite}60` }}>Instant victory check after every execution</span>
          </div>
        </FadeIn>
      </div>
    </div>
  );
};
