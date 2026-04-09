"use client";

import { useState } from "react";
import type { SimulationConfig } from "@/lib/api";

interface Props {
  onStart: (config: SimulationConfig) => void;
  isRunning: boolean;
}

export function SimulationControls({ onStart, isRunning }: Props) {
  const [maxTurns, setMaxTurns] = useState(20);
  const [dmStaleTurns, setDmStaleTurns] = useState(2);
  const [width, setWidth] = useState(8);
  const [height, setHeight] = useState(8);
  const [seed, setSeed] = useState("");
  const [expanded, setExpanded] = useState(false);

  function handleStart() {
    onStart({
      max_turns: maxTurns,
      dm_stale_turns: dmStaleTurns,
      width,
      height,
      wall_density: 0.15,
      seed: seed ? parseInt(seed, 10) : null,
    });
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={handleStart}
            disabled={isRunning}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isRunning
                ? "bg-zinc-700 text-zinc-400 cursor-not-allowed"
                : "bg-emerald-600 hover:bg-emerald-500 text-white"
            }`}
          >
            {isRunning ? (
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-zinc-400 border-t-white rounded-full animate-spin" />
                Running Simulation…
              </span>
            ) : (
              "▶ Start Simulation"
            )}
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            {expanded ? "▾ Hide Config" : "▸ Config"}
          </button>
        </div>

        {!expanded && (
          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span>{width}×{height} grid</span>
            <span>{maxTurns} turns</span>
            <span>DM lag: {dmStaleTurns}</span>
            {seed && <span>seed: {seed}</span>}
          </div>
        )}
      </div>

      {expanded && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4 pt-4 border-t border-zinc-800">
          <Field label="Grid Width" min={4} max={20} value={width} onChange={setWidth} />
          <Field label="Grid Height" min={4} max={20} value={height} onChange={setHeight} />
          <Field label="Max Turns" min={1} max={500} value={maxTurns} onChange={setMaxTurns} />
          <Field label="DM State Lag" min={0} max={10} value={dmStaleTurns} onChange={setDmStaleTurns} />
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Seed (optional)</label>
            <input
              type="text"
              placeholder="Random"
              value={seed}
              onChange={(e) => setSeed(e.target.value.replace(/\D/g, ""))}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-500"
            />
          </div>
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  min,
  max,
  value,
  onChange,
}: {
  label: string;
  min: number;
  max: number;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="block text-xs text-zinc-500 mb-1">{label}</label>
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => {
          const v = parseInt(e.target.value, 10);
          if (!isNaN(v) && v >= min && v <= max) onChange(v);
        }}
        className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-zinc-500"
      />
    </div>
  );
}
