import { create } from "zustand";

type AnalysisState = {
  severity: string | null;
  category: string | null;
  selectSeverity: (value: string | null) => void;
  selectCategory: (value: string | null) => void;
};

export const useAnalysisStore = create<AnalysisState>((set) => ({
  severity: null,
  category: null,
  selectSeverity: (severity) => set({ severity }),
  selectCategory: (category) => set({ category }),
}));
