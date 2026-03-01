import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";
import { FadeIn } from "../components/GoldText";

const ChatBubble: React.FC<{
  name: string;
  role_en: string;
  text: string;
  isPlayer?: boolean;
  delay: number;
}> = ({ name, role_en, text, isPlayer = false, delay }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [delay, delay + 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const roleColor: Record<string, string> = {
    FUGO: COLORS.gold,
    HINMIN: "#d06060",
    HEIMIN: "#a0a090",
    PLAYER: "#60a0e0",
    DETECTIVE: "#80d0c0",
  };
  const color = roleColor[role_en] ?? COLORS.dimWhite;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: isPlayer ? "row-reverse" : "row",
        alignItems: "flex-start",
        gap: 10,
        opacity: p,
        transform: `translateX(${(1 - p) * (isPlayer ? 16 : -16)}px)`,
        marginBottom: 8,
      }}
    >
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: "50%",
          background: `${color}22`,
          border: `1.5px solid ${color}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 11,
          color,
          fontWeight: 700,
          flexShrink: 0,
          fontFamily: '"Noto Sans JP", sans-serif',
        }}
      >
        {name[0]}
      </div>
      <div style={{ maxWidth: "78%" }}>
        <div
          style={{
            fontSize: 10,
            color,
            marginBottom: 3,
            letterSpacing: 1,
            fontFamily: '"Noto Sans JP", sans-serif',
          }}
        >
          {name}{" "}
          <span style={{ color: `${color}70`, fontSize: 9 }}>[{role_en}]</span>
        </div>
        <div
          style={{
            background: isPlayer ? "#101a28" : COLORS.panel,
            border: `1px solid ${color}35`,
            borderRadius: isPlayer ? "12px 4px 12px 12px" : "4px 12px 12px 12px",
            padding: "7px 13px",
            fontSize: 13,
            color: COLORS.white,
            lineHeight: 1.65,
            fontFamily: '"Noto Sans JP", sans-serif',
          }}
        >
          {text}
        </div>
      </div>
    </div>
  );
};

// 24–50s (720–1500 frames)
export const DayScene: React.FC = () => {
  const frame = useCurrentFrame();

  const chats = [
    {
      name: "桐嶋 源治",
      role_en: "FUGO",
      text: "昨夜のカードの流れ、不自然だった。誰かが情報を持っている……",
      delay: 12,
    },
    {
      name: "You",
      role_en: "PLAYER",
      text: "I don't remember much. But something feels off about the votes.",
      isPlayer: true,
      delay: 30,
    },
    {
      name: "宮本 沙也",
      role_en: "HINMIN",
      text: "都合よく「記憶がない」って、怪しくない？証拠はないけど確信がある",
      delay: 50,
    },
    {
      name: "田中 一郎",
      role_en: "DETECTIVE",
      text: "Let's focus on facts. Who benefits if we execute next?",
      delay: 70,
    },
  ];

  const voteAnim = interpolate(frame, [110, 140], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const execAnim = interpolate(frame, [160, 180], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const votes = [
    { name: "桐嶋 源治", tag: "FUGO", count: 3, max: 4, color: COLORS.gold },
    { name: "宮本 沙也", tag: "HINMIN", count: 1, max: 4, color: "#d06060" },
    { name: "田中 一郎", tag: "DETECTIVE", count: 0, max: 4, color: "#80d0c0" },
  ];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: `radial-gradient(ellipse at 30% 40%, #0e0c08 0%, ${COLORS.bg} 60%)`,
        display: "flex",
        fontFamily: '"Noto Sans JP", sans-serif',
        padding: "36px 52px",
        boxSizing: "border-box",
        gap: 36,
      }}
    >
      {/* LEFT: Chat */}
      <div style={{ flex: 1.5, display: "flex", flexDirection: "column" }}>
        <FadeIn delay={0} duration={14}>
          <div
            style={{
              fontSize: 10,
              color: COLORS.goldDim,
              letterSpacing: 5,
              marginBottom: 4,
            }}
          >
            PHASE 01 — DAY / 昼の会議
          </div>
          <div
            style={{
              fontSize: 26,
              color: COLORS.white,
              fontWeight: 700,
              marginBottom: 4,
            }}
          >
            議論・投票・処刑
          </div>
          <div style={{ fontSize: 13, color: COLORS.dimWhite, marginBottom: 20 }}>
            Discuss and deduce — then vote to execute.
          </div>
        </FadeIn>

        {chats.map((c, i) => (
          <ChatBubble key={i} {...c} />
        ))}

        {/* NPC strategy note */}
        <FadeIn delay={100} duration={18}>
          <div
            style={{
              marginTop: 12,
              padding: "10px 16px",
              background: "#0e0e14",
              border: `1px solid ${COLORS.goldDim}40`,
              borderRadius: 8,
              fontSize: 12,
              color: COLORS.dimWhite,
              lineHeight: 1.7,
            }}
          >
            NPCは各自の{" "}
            <span style={{ color: COLORS.gold }}>SECRET MISSION</span>{" "}
            に従い発言・投票を戦略的に行う
          </div>
        </FadeIn>
      </div>

      {/* RIGHT: Vote panel */}
      <div
        style={{
          flex: 0.85,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        {/* Vote tally */}
        <FadeIn delay={96} duration={18}>
          <div
            style={{
              background: COLORS.panel,
              border: `1px solid ${COLORS.goldDim}`,
              borderRadius: 10,
              padding: "18px 20px",
            }}
          >
            <div
              style={{
                fontSize: 10,
                color: COLORS.goldDim,
                letterSpacing: 4,
                marginBottom: 14,
              }}
            >
              VOTE TALLY — 投票集計
            </div>
            {votes.map((v, i) => (
              <div key={i} style={{ marginBottom: 13 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 4,
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: 13, color: v.color }}>
                    {v.name}{" "}
                    <span style={{ fontSize: 9, color: `${v.color}80` }}>[{v.tag}]</span>
                  </span>
                  <span style={{ fontSize: 13, color: v.color }}>{v.count} votes</span>
                </div>
                <div style={{ background: "#1a1a20", borderRadius: 4, height: 5 }}>
                  <div
                    style={{
                      background: v.color,
                      borderRadius: 4,
                      height: 5,
                      width: `${(v.count / v.max) * 100 * voteAnim}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </FadeIn>

        {/* Execution */}
        <div style={{ opacity: execAnim, transform: `scale(${0.94 + execAnim * 0.06})` }}>
          <div
            style={{
              background: "#200808",
              border: "1.5px solid #802020",
              borderRadius: 10,
              padding: "16px 20px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: 10,
                color: "#ff6060",
                letterSpacing: 4,
                marginBottom: 8,
              }}
            >
              EXECUTED — 処刑
            </div>
            <div style={{ fontSize: 22, color: COLORS.white, fontWeight: 700 }}>
              桐嶋 源治
            </div>
            <div style={{ fontSize: 11, color: COLORS.dimWhite, marginTop: 5 }}>
              最多得票により追放 · Most votes received
            </div>
          </div>
        </div>

        {/* Victory check reminder */}
        <FadeIn delay={185} duration={18}>
          <div
            style={{
              padding: "10px 16px",
              background: "#0a0a14",
              border: `1px solid #4040a060`,
              borderRadius: 8,
              fontSize: 12,
              color: COLORS.dimWhite,
              lineHeight: 1.7,
            }}
          >
            処刑直後に <span style={{ color: "#8080e0" }}>SECRET MISSION</span> を即座にチェック
            <br />
            <span style={{ fontSize: 10, color: `${COLORS.dimWhite}80` }}>
              Instant victory check after every execution
            </span>
          </div>
        </FadeIn>
      </div>
    </div>
  );
};
