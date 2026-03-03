import { useState } from 'react';
import type { ViewMode } from './ViewChartToggle';

export const useViewToggle = (defaultView: ViewMode = 'table') => {
  const [view, setView] = useState<ViewMode>(defaultView);
  return { view, setView };
};
