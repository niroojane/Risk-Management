import { create } from 'zustand';

interface UIState {
  openMenus: Record<string, boolean>;
  toggleMenu: (label: string) => void;
}

export const useUIStore = create<UIState>()((set) => ({
  openMenus: {},
  toggleMenu: (label) =>
    set((state) => ({
      openMenus: { ...state.openMenus, [label]: !state.openMenus[label] },
    })),
}));
