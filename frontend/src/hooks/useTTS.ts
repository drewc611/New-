import { create } from "zustand";
import { useEffect } from "react";

interface TTSState {
  enabled: boolean;
  speakingId: string | null;
  toggleEnabled: () => void;
  setEnabled: (v: boolean) => void;
  speak: (id: string, text: string) => void;
  stop: () => void;
}

const stripMarkdown = (md: string): string =>
  md
    .replace(/```[\s\S]*?```/g, " code block ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[*_~>#-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const synth: SpeechSynthesis | null =
  typeof window !== "undefined" && "speechSynthesis" in window
    ? window.speechSynthesis
    : null;

export const useTTS = create<TTSState>((set, get) => ({
  enabled: true,
  speakingId: null,

  toggleEnabled: () => {
    const next = !get().enabled;
    if (!next && synth) synth.cancel();
    set({ enabled: next, speakingId: next ? get().speakingId : null });
  },

  setEnabled: (v: boolean) => {
    if (!v && synth) synth.cancel();
    set({ enabled: v, speakingId: v ? get().speakingId : null });
  },

  speak: (id: string, text: string) => {
    if (!synth) return;
    synth.cancel();
    const clean = stripMarkdown(text);
    if (!clean) return;
    const utter = new SpeechSynthesisUtterance(clean);
    utter.rate = 1;
    utter.pitch = 1;
    utter.volume = 1;
    utter.onend = () => {
      if (get().speakingId === id) set({ speakingId: null });
    };
    utter.onerror = () => {
      if (get().speakingId === id) set({ speakingId: null });
    };
    set({ speakingId: id });
    synth.speak(utter);
  },

  stop: () => {
    if (synth) synth.cancel();
    set({ speakingId: null });
  },
}));

export const ttsSupported = (): boolean => synth !== null;

export function useStopTTSOnUnmount() {
  const stop = useTTS((s) => s.stop);
  useEffect(() => () => stop(), [stop]);
}
