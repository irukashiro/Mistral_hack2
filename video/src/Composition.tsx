import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { TitleScene } from "./scenes/TitleScene";
import { ConceptScene } from "./scenes/ConceptScene";
import { DayScene } from "./scenes/DayScene";
import { CheatScene } from "./scenes/CheatScene";
import { NightScene } from "./scenes/NightScene";
import { AIScene } from "./scenes/AIScene";
import { EndScene } from "./scenes/EndScene";
import { COLORS } from "./theme";

// Total: 120s × 30fps = 3600 frames
//
// Scene        Start   End    Duration  Seconds
// Title        0       240    240       0–8s
// Concept      240     720    480       8–24s
// Day          720     1500   780       24–50s
// Cheat        1500    2280   780       50–76s
// Night        2280    2940   660       76–98s
// AI           2940    3390   450       98–113s
// End          3390    3600   210       113–120s

export const MainComposition: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <Sequence from={0} durationInFrames={240}>
        <TitleScene />
      </Sequence>

      <Sequence from={240} durationInFrames={480}>
        <ConceptScene />
      </Sequence>

      <Sequence from={720} durationInFrames={780}>
        <DayScene />
      </Sequence>

      <Sequence from={1500} durationInFrames={780}>
        <CheatScene />
      </Sequence>

      <Sequence from={2280} durationInFrames={660}>
        <NightScene />
      </Sequence>

      <Sequence from={2940} durationInFrames={450}>
        <AIScene />
      </Sequence>

      <Sequence from={3390} durationInFrames={210}>
        <EndScene />
      </Sequence>
    </AbsoluteFill>
  );
};
