import React from "react";
import { Composition } from "remotion";
import { MainComposition } from "./Composition";
import { FPS, TOTAL_FRAMES } from "./theme";

export const Root: React.FC = () => {
  return (
    <Composition
      id="MainComposition"
      component={MainComposition}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={1280}
      height={720}
    />
  );
};
