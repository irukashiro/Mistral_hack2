import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { TitleScene } from "./scenes/TitleScene";
import { ConceptScene } from "./scenes/ConceptScene";
import { RolesScene } from "./scenes/RolesScene";
import { DayScene } from "./scenes/DayScene";
import { CheatScene } from "./scenes/CheatScene";
import { NightScene } from "./scenes/NightScene";
import { LogicScene } from "./scenes/LogicScene";
import { AIScene } from "./scenes/AIScene";
import { EndScene } from "./scenes/EndScene";
import { SubtitleOverlay } from "./components/Subtitles";
import { COLORS } from "./theme";
import { TOTAL_FRAMES } from "./theme";

// Total: 120s × 30fps = 3600 frames
//
// Scene     Start  End    Frames  Seconds  Source
// Title      0     150    150      0–5s    タイトル
// Concept    150   510    360      5–17s   SETTING.md v2.0 世界観
// Roles      510   900    390     17–30s   SETTING.md v4.0 2層構造
// Day        900  1410    510     30–47s   SETTING.md v3.0/v4.0 昼フェーズ・性格
// Cheat     1410  1860    450     47–62s   SETTING.md v3.0 陽動システム
// Night     1860  2220    360     62–74s   SETTING.md v4.0 夜・関係値
// Logic     2220  2760    540     74–92s   SETTING.md Logic State Manager
// AI        2760  3210    450     92–107s  AI統合
// End       3210  3600    390    107–120s  エンドカード

export const MainComposition: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <Sequence from={0} durationInFrames={150}>
        <TitleScene />
      </Sequence>
      <Sequence from={150} durationInFrames={360}>
        <ConceptScene />
      </Sequence>
      <Sequence from={510} durationInFrames={390}>
        <RolesScene />
      </Sequence>
      <Sequence from={900} durationInFrames={510}>
        <DayScene />
      </Sequence>
      <Sequence from={1410} durationInFrames={450}>
        <CheatScene />
      </Sequence>
      <Sequence from={1860} durationInFrames={360}>
        <NightScene />
      </Sequence>
      <Sequence from={2220} durationInFrames={540}>
        <LogicScene />
      </Sequence>
      <Sequence from={2760} durationInFrames={450}>
        <AIScene />
      </Sequence>
      <Sequence from={3210} durationInFrames={390}>
        <EndScene />
      </Sequence>

      {/* Subtitle overlay — spans full video */}
      <Sequence from={0} durationInFrames={TOTAL_FRAMES}>
        <SubtitleOverlay />
      </Sequence>
    </AbsoluteFill>
  );
};
