import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";

export interface SubtitleEntry {
  from: number;
  to: number;
  ja: string;
  en: string;
}

export const SUBTITLES: SubtitleEntry[] = [
  // ── TitleScene (0–150) ── Slide 1
  {
    from: 38, to: 148,
    ja: "全く新しいデスゲーム・アドベンチャーをご提案します。",
    en: "A brand-new death-game adventure unlike anything you've played.",
  },

  // ── ConceptScene (150–510) ── Slide 2
  {
    from: 168, to: 338,
    ja: "閉鎖空間に集められた5人。AIが毎回ランダムな人間関係を自動生成します。",
    en: "5 strangers in a locked room. AI generates unique relationships every playthrough.",
  },
  {
    from: 348, to: 508,
    ja: "カードの強さではなく、いかに他者を騙し、味方につけ、邪魔者を処刑するか——",
    en: "It's not about card strength — it's about deception, alliance, and execution.",
  },

  // ── RolesScene (510–900) ── Slide 2続き
  {
    from: 528, to: 710,
    ja: "多数派の平民、逃げ切りを狙う富豪、イカサマで場を荒らす貧民——三つ巴の非対称戦。",
    en: "Commoners vs. the Rich vs. the Poor — asymmetric three-faction warfare.",
  },
  {
    from: 720, to: 898,
    ja: "探偵・ボディガード・共犯者の役職とTrue Win（個人勝利条件）もAIが自動生成。",
    en: "Detective, Bodyguard, Accomplice — plus AI-generated secret victory conditions.",
  },

  // ── DayScene (900–1410) ── Slide 3昼 + Slide 5
  {
    from: 918, to: 1100,
    ja: "昼の会議では夜のプレイ内容を証拠として突きつけ合い、誰を処刑するかを決定します。",
    en: "In the day meeting, last night's card plays become evidence for the vote.",
  },
  {
    from: 1108, to: 1288,
    ja: "NPCは論理型・感情型・ヘイト回避型・破滅型の4つの性格で動きます。",
    en: "NPCs run on 4 personality types: Logical, Emotional, Passive, and Chaotic.",
  },
  {
    from: 1295, to: 1408,
    ja: "カードのプレイングそのものが、命を左右する証拠になるのです。",
    en: "Every card you play is a clue that can save — or cost — your life.",
  },

  // ── CheatScene (1410–1860) ── Slide 4
  {
    from: 1428, to: 1600,
    ja: "最大の目玉は生成AIを使った『イカサマ』システム。陽動と本命をテキストで自由入力します。",
    en: "The highlight: an AI-judged cheat system. Enter your Decoy and Real Action freely.",
  },
  {
    from: 1608, to: 1780,
    ja: "狙われた側は突然表示される陽動に対し、5秒以内・15文字以内でリアクションを返さなければなりません。",
    en: "The target must react to the decoy within 5 seconds and 15 characters.",
  },
  {
    from: 1788, to: 1858,
    ja: "言葉による生々しい騙し合い——Mistral AIが成功を裁きます。",
    en: "Raw verbal deception — judged in real time by Mistral AI.",
  },

  // ── NightScene (1860–2220) ── Slide 3夜
  {
    from: 1878, to: 2050,
    ja: "夜はAIキャラクターが強いカードに反応して疑惑を煽り、疑心暗鬼を生み出します。",
    en: "At night, NPCs react to strong cards with suspicion, fueling paranoia.",
  },
  {
    from: 2058, to: 2218,
    ja: "NPCは関係値マトリックスに基づき、味方にはパスを回し、敵には強いカードをぶつけます。",
    en: "NPCs pass to allies and attack enemies — driven by Trust × Affinity scores.",
  },

  // ── LogicScene (2220–2760) ── Slide 5
  {
    from: 2238, to: 2430,
    ja: "NPCのAIは人狼セオリーを自ら導き出します——ローラー作戦、確定白、ライン考察。",
    en: "NPC AI derives werewolf tactics on its own: Roller, Confirmed White, Line Theory.",
  },
  {
    from: 2438, to: 2618,
    ja: "感情型AIはロジックを理解した上で「でも私はあの人が好きだからかばう！」と動きます。",
    en: "The Emotional AI understands logic — then ignores it to protect someone it likes.",
  },
  {
    from: 2625, to: 2758,
    ja: "この人間くさい矛盾が、極上のドラマを生み出すのです。",
    en: "This very human contradiction is what creates extraordinary drama.",
  },

  // ── AIScene (2760–3210) ── Slide 6
  {
    from: 2778, to: 2960,
    ja: "遊びやすさに徹底的にこだわり、AIが常に発言を提案。会話のヒントを自動メモします。",
    en: "Accessibility first — AI suggests dialogue, and auto-logs conversational clues.",
  },
  {
    from: 2968, to: 3130,
    ja: "処刑されても終わりではありません。神の目モードで全キャラの真相を見届けられます。",
    en: "Even after execution, you watch the drama unfold with full God's-Eye visibility.",
  },
  {
    from: 3138, to: 3208,
    ja: "Mistral AIがすべての世界・キャラクター・因縁を自動生成します。",
    en: "Mistral AI generates the entire world, cast, and backstories from scratch.",
  },

  // ── EndScene (3210–3600) ── Slide 7
  {
    from: 3228, to: 3400,
    ja: "ゲーム終了後、すべての真実が開示されます——隠された人間関係、強烈なアハ体験。",
    en: "At game end, all secrets are revealed — hidden bonds, shocking twists.",
  },
  {
    from: 3408, to: 3558,
    ja: "一度このカタルシスを味わえば、何度でも別の設定でループしたくなる。",
    en: "Once you feel this catharsis, you'll want to replay it again and again.",
  },
  {
    from: 3563, to: 3598,
    ja: "それが『Class Conflict : Millionaire』です。",
    en: "That is Class Conflict: Millionaire.",
  },
];

export const SubtitleOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  const current = SUBTITLES.find((s) => frame >= s.from && frame < s.to) ?? null;

  const FADE = 8;
  const opacity = current
    ? interpolate(
        frame,
        [current.from, current.from + FADE, current.to - FADE, current.to],
        [0, 1, 1, 0],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
      )
    : 0;

  if (!current) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 28,
        left: "50%",
        transform: "translateX(-50%)",
        opacity,
        zIndex: 100,
        textAlign: "center",
        pointerEvents: "none",
        maxWidth: 1000,
        width: "90%",
      }}
    >
      {/* Backdrop */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "rgba(0,0,0,0.75)",
          borderRadius: 8,
          backdropFilter: "blur(2px)",
        }}
      />
      <div
        style={{
          position: "relative",
          padding: "9px 26px 10px",
          borderTop: `2px solid ${COLORS.gold}55`,
        }}
      >
        {/* Japanese — primary, large */}
        <div
          style={{
            fontSize: 17,
            color: COLORS.white,
            fontFamily: '"Noto Sans JP", sans-serif',
            fontWeight: 500,
            lineHeight: 1.6,
            textShadow: "0 1px 4px rgba(0,0,0,0.9)",
            letterSpacing: 0.3,
          }}
        >
          {current.ja}
        </div>
        {/* English — secondary, smaller, dimmed */}
        <div
          style={{
            fontSize: 12,
            color: COLORS.dimWhite,
            fontFamily: '"Noto Sans JP", sans-serif',
            fontWeight: 400,
            lineHeight: 1.5,
            marginTop: 3,
            textShadow: "0 1px 3px rgba(0,0,0,0.9)",
            letterSpacing: 0.5,
            opacity: 0.85,
          }}
        >
          {current.en}
        </div>
      </div>
    </div>
  );
};
