import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

// 50–76s (1500–2280 frames) — localFrame
export const CheatScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const timerWidth = interpolate(frame, [70, 240], [100, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const timerColor = timerWidth > 40
    ? "linear-gradient(90deg,#3060e0,#60a0ff)"
    : "linear-gradient(90deg,#e03020,#ff7060)";

  const resultAnim = interpolate(frame, [220, 248], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const shakeSpring = spring({ fps, frame: frame - 218, config: { stiffness: 320, damping: 7 } });
  const shakeX = frame >= 218 && frame < 250 ? Math.sin(frame * 2) * 5 * Math.max(0, 1 - shakeSpring) : 0;

  const outcomes = [
    { en: "BIG SUCCESS", ja: "大成功", sub: "陽動に引っかかる → カード強奪・バレない", color: COLORS.gold },
    { en: "DRAW", ja: "引き分け", sub: "本命をガード → 失敗するが正体不明", color: "#8080c0" },
    { en: "BIG FAIL", ja: "大失敗", sub: "完全防御 → イカサマがバレて露見", color: "#c04040" },
  ];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: `radial-gradient(ellipse at 50% 40%, #1a0808 0%, ${COLORS.bg} 65%)`,
        display: "flex",
        flexDirection: "column",
        fontFamily: '"Noto Sans JP", sans-serif',
        padding: "32px 56px",
        boxSizing: "border-box",
      }}
    >
      {/* Header */}
      <FadeIn delay={0} duration={16}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 10, color: "#e06060", letterSpacing: 5, marginBottom: 6 }}>
            CHEAT PHASE — イカサマ対決
          </div>
          <div style={{ fontSize: 28, color: COLORS.white, fontWeight: 700, marginBottom: 4 }}>
            陽動イカサマシステム
          </div>
          {/* AGENTS.md key description */}
          <div style={{ fontSize: 14, color: COLORS.dimWhite, lineHeight: 1.6 }}>
            貧民だけが持つ、下克上の切り札。
            <span style={{ color: COLORS.gold }}> 自由なプロンプト</span>で「ズルの手口」と「対策」を入力し、
            AIが成功を裁く。
            <span style={{ color: `${COLORS.dimWhite}70`, fontSize: 12, display: "block", marginTop: 2 }}>
              The underclass's wildcard — free-form prompts judged by AI.
            </span>
          </div>
        </div>
      </FadeIn>

      {/* Main duel */}
      <div
        style={{
          display: "flex",
          gap: 20,
          flex: 1,
          transform: `translateX(${shakeX}px)`,
        }}
      >
        {/* Attacker */}
        <FadeIn delay={22} duration={18} style={{ flex: 1 }}>
          <div
            style={{
              background: "#180808",
              border: "1px solid #7a2020",
              borderRadius: 12,
              padding: "20px 22px",
              height: "100%",
              boxSizing: "border-box",
            }}
          >
            <div style={{ fontSize: 10, color: "#e07060", letterSpacing: 3, marginBottom: 14 }}>
              ATTACKER / 仕掛ける側（貧民）
            </div>

            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, color: COLORS.dimWhite, marginBottom: 6, letterSpacing: 1 }}>
                DECOY / 陽動
              </div>
              <div
                style={{
                  background: "#100606",
                  border: "1px solid #501818",
                  borderRadius: 8,
                  padding: "10px 14px",
                  fontSize: 13,
                  color: COLORS.white,
                  fontStyle: "italic",
                  lineHeight: 1.65,
                }}
              >
                「うわっ、虫！」と叫びながら天井を指さす
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, color: COLORS.dimWhite, marginBottom: 6, letterSpacing: 1 }}>
                REAL ACTION / 本命
              </div>
              <div
                style={{
                  background: "#100606",
                  border: "1px solid #501818",
                  borderRadius: 8,
                  padding: "10px 14px",
                  fontSize: 13,
                  color: COLORS.white,
                  fontStyle: "italic",
                  lineHeight: 1.65,
                }}
              >
                相手が上を向いた隙に右端のカードを素早く抜く
              </div>
            </div>
          </div>
        </FadeIn>

        {/* VS */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 22,
            color: COLORS.gold,
            fontWeight: 900,
            width: 36,
            flexShrink: 0,
          }}
        >
          VS
        </div>

        {/* Defender */}
        <FadeIn delay={42} duration={18} style={{ flex: 1 }}>
          <div
            style={{
              background: "#080a1c",
              border: "1px solid #203080",
              borderRadius: 12,
              padding: "20px 22px",
              height: "100%",
              boxSizing: "border-box",
            }}
          >
            <div style={{ fontSize: 10, color: "#7090e0", letterSpacing: 3, marginBottom: 14 }}>
              DEFENDER / 防衛側
            </div>

            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, color: COLORS.dimWhite, marginBottom: 6, letterSpacing: 1 }}>
                REACTION / リアクション
              </div>
              <div
                style={{
                  background: "#080c18",
                  border: "1px solid #1a2050",
                  borderRadius: 8,
                  padding: "10px 14px",
                  fontSize: 13,
                  color: COLORS.white,
                  fontStyle: "italic",
                }}
              >
                素早く手を押さえる
              </div>
            </div>

            {/* Constraints */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", gap: 10 }}>
                {["15 chars max", "5 sec limit"].map((c, i) => (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      background: "#0a0c1a",
                      border: "1px solid #2030604",
                      borderRadius: 6,
                      padding: "6px",
                      textAlign: "center",
                      fontSize: 11,
                      color: "#6080c0",
                      letterSpacing: 0.5,
                    }}
                  >
                    {c}
                  </div>
                ))}
              </div>
            </div>

            {/* Timer bar */}
            <div style={{ fontSize: 10, color: COLORS.dimWhite, marginBottom: 5, letterSpacing: 1 }}>
              TIME REMAINING
            </div>
            <div style={{ background: "#111", borderRadius: 4, height: 7, overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  borderRadius: 4,
                  width: `${timerWidth}%`,
                  background: timerColor,
                }}
              />
            </div>
          </div>
        </FadeIn>
      </div>

      {/* Outcome legend */}
      <FadeIn delay={68} duration={20}>
        <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
          {outcomes.map((o, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                background: COLORS.panel,
                border: `1px solid ${o.color}40`,
                borderRadius: 8,
                padding: "10px 14px",
              }}
            >
              <div style={{ fontSize: 10, color: o.color, letterSpacing: 2, marginBottom: 3 }}>
                {o.en}
              </div>
              <div style={{ fontSize: 14, color: o.color, fontWeight: 700, marginBottom: 4 }}>
                {o.ja}
              </div>
              <div style={{ fontSize: 11, color: COLORS.dimWhite, lineHeight: 1.5 }}>{o.sub}</div>
            </div>
          ))}
        </div>
      </FadeIn>

      {/* Result flash */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: "50%",
          transform: `translateX(-50%) scale(${0.85 + resultAnim * 0.15})`,
          opacity: resultAnim,
          textAlign: "center",
          background: "#180e00",
          border: `2px solid ${COLORS.gold}`,
          borderRadius: 12,
          padding: "14px 48px",
          pointerEvents: "none",
        }}
      >
        <div style={{ fontSize: 9, color: COLORS.goldDim, letterSpacing: 4, marginBottom: 4 }}>
          JUDGMENT
        </div>
        <div style={{ fontSize: 28, color: COLORS.goldLight, fontWeight: 900 }}>
          BIG SUCCESS — 大成功
        </div>
        <div style={{ fontSize: 12, color: COLORS.dimWhite, marginTop: 4 }}>
          カード1枚強奪。誰にもバレない。
        </div>
      </div>
    </div>
  );
};
