import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 47–62s (1410–1860 frames) — localFrame  SETTING.md v3.0 陽動システム
export const CheatScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const timerW = interpolate(frame, [60, 200], [100, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const timerColor = timerW > 40
    ? "linear-gradient(90deg,#3060e0,#60a0ff)"
    : "linear-gradient(90deg,#e03020,#ff7060)";

  const resultAnim = interpolate(frame, [210, 232], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const shakeSpring = spring({ fps, frame: frame - 208, config: { stiffness: 320, damping: 7 } });
  const shakeX = frame >= 208 && frame < 240 ? Math.sin(frame * 2) * 4 * Math.max(0, 1 - shakeSpring) : 0;

  const outcomes = [
    { en: "BIG SUCCESS", ja: "大成功", sub: "陽動に引っかかる or 時間切れ → 強奪・バレない", color: COLORS.gold },
    { en: "DRAW", ja: "引き分け", sub: "本命をガード → 失敗、バレない", color: "#8080c0" },
    { en: "BIG FAIL", ja: "大失敗", sub: "物理制圧で完全防御 → 露見", color: "#c04040" },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: `radial-gradient(ellipse at 50% 40%, #1a0808 0%, ${COLORS.bg} 65%)`,
      display: "flex", flexDirection: "column", fontFamily: '"Noto Sans JP",sans-serif',
      padding: "24px 48px", boxSizing: "border-box",
    }}>
      <FadeIn delay={0} duration={12}>
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 10, color: "#e06060", letterSpacing: 5, marginBottom: 5 }}>CHEAT PHASE — イカサマ対決</div>
          <div style={{ fontSize: 24, color: COLORS.white, fontWeight: 700, marginBottom: 3 }}>陽動イカサマシステム</div>
          <div style={{ fontSize: 13, color: COLORS.dimWhite, lineHeight: 1.6 }}>
            貧民専用の切り札。<span style={{ color: COLORS.gold }}>自由プロンプト</span>で手口を入力し、AIが裁く。
            <span style={{ color: `${COLORS.dimWhite}70`, fontSize: 11, display: "block" }}>
              Free-form prompts — Decoy + Real Action. Judged by mistral-large.
            </span>
          </div>
        </div>
      </FadeIn>

      <div style={{ display: "flex", gap: 18, flex: 1, transform: `translateX(${shakeX}px)` }}>
        {/* Attacker */}
        <FadeIn delay={18} duration={14} style={{ flex: 1 }}>
          <div style={{ background: "#180808", border: "1px solid #7a2020", borderRadius: 12, padding: "16px 18px", height: "100%", boxSizing: "border-box" }}>
            <div style={{ fontSize: 10, color: "#e07060", letterSpacing: 3, marginBottom: 12 }}>ATTACKER / 仕掛ける側（貧民）</div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: COLORS.dimWhite, marginBottom: 5, letterSpacing: 1 }}>DECOY / 陽動</div>
              <div style={{ background: "#100606", border: "1px solid #501818", borderRadius: 7, padding: "8px 12px", fontSize: 13, color: COLORS.white, fontStyle: "italic", lineHeight: 1.6 }}>
                「うわっ、虫！」と叫びながら天井を指さす
              </div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: COLORS.dimWhite, marginBottom: 5, letterSpacing: 1 }}>REAL ACTION / 本命</div>
              <div style={{ background: "#100606", border: "1px solid #501818", borderRadius: 7, padding: "8px 12px", fontSize: 13, color: COLORS.white, fontStyle: "italic", lineHeight: 1.6 }}>
                相手が上を向いた隙に右端のカードを素早く抜く
              </div>
            </div>
          </div>
        </FadeIn>

        <div style={{ display: "flex", alignItems: "center", fontSize: 20, color: COLORS.gold, fontWeight: 900, width: 32, flexShrink: 0 }}>VS</div>

        {/* Defender */}
        <FadeIn delay={34} duration={14} style={{ flex: 1 }}>
          <div style={{ background: "#080a1c", border: "1px solid #203080", borderRadius: 12, padding: "16px 18px", height: "100%", boxSizing: "border-box" }}>
            <div style={{ fontSize: 10, color: "#7090e0", letterSpacing: 3, marginBottom: 12 }}>DEFENDER / 防衛側</div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: COLORS.dimWhite, marginBottom: 5, letterSpacing: 1 }}>REACTION / リアクション（陽動のみ表示）</div>
              <div style={{ background: "#080c18", border: "1px solid #1a2050", borderRadius: 7, padding: "8px 12px", fontSize: 13, color: COLORS.white, fontStyle: "italic" }}>
                素早く手を押さえる
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              {["15 chars max", "5 sec limit"].map((c, i) => (
                <div key={i} style={{ flex: 1, background: "#0a0c1a", border: "1px solid #202060", borderRadius: 5, padding: "5px", textAlign: "center", fontSize: 10, color: "#6080c0" }}>{c}</div>
              ))}
            </div>
            <div style={{ fontSize: 10, color: COLORS.dimWhite, marginBottom: 4, letterSpacing: 1 }}>TIME REMAINING</div>
            <div style={{ background: "#111", borderRadius: 4, height: 6, overflow: "hidden" }}>
              <div style={{ height: "100%", borderRadius: 4, width: `${timerW}%`, background: timerColor }} />
            </div>
          </div>
        </FadeIn>
      </div>

      {/* Outcomes */}
      <FadeIn delay={56} duration={14}>
        <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
          {outcomes.map((o, i) => (
            <div key={i} style={{ flex: 1, background: COLORS.panel, border: `1px solid ${o.color}40`, borderRadius: 7, padding: "8px 12px" }}>
              <div style={{ fontSize: 9, color: o.color, letterSpacing: 2, marginBottom: 2 }}>{o.en}</div>
              <div style={{ fontSize: 13, color: o.color, fontWeight: 700, marginBottom: 3 }}>{o.ja}</div>
              <div style={{ fontSize: 11, color: COLORS.dimWhite, lineHeight: 1.5 }}>{o.sub}</div>
            </div>
          ))}
        </div>
      </FadeIn>

      {/* Result flash */}
      <div style={{
        position: "absolute", bottom: 28, left: "50%",
        transform: `translateX(-50%) scale(${0.88 + resultAnim * 0.12})`,
        opacity: resultAnim, textAlign: "center",
        background: "#180e00", border: `2px solid ${COLORS.gold}`, borderRadius: 10, padding: "12px 44px",
      }}>
        <div style={{ fontSize: 9, color: COLORS.goldDim, letterSpacing: 4, marginBottom: 3 }}>JUDGMENT</div>
        <div style={{ fontSize: 26, color: COLORS.goldLight, fontWeight: 900 }}>BIG SUCCESS — 大成功</div>
        <div style={{ fontSize: 11, color: COLORS.dimWhite, marginTop: 3 }}>カード1枚強奪。誰にもバレない。</div>
      </div>
    </div>
  );
};
