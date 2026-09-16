import { useMemo } from 'react';
import { useTheme } from './useTheme';

export interface ChartThemeTokens {
  isDark: boolean;
  grid: string;
  axis: string;
  text: string;
  muted: string;
  border: string;
  tooltipBg: string;
  tooltipBorder: string;
  tooltipShadow: string;
  accent: string;
  accentHover: string;
  accentSoft: string;
  positive: string;
  negative: string;
  warning: string;
  info: string;
  allocationPalette: string[];
}

const LIGHT_TOKENS: ChartThemeTokens = {
  isDark: false,
  grid: '#E2E8E3',
  axis: '#68736C',
  text: '#18221C',
  muted: '#8A948D',
  border: '#DCE3DD',
  tooltipBg: '#FFFFFF',
  tooltipBorder: '#DCE3DD',
  tooltipShadow: '0 4px 14px rgba(24, 34, 28, 0.08)',
  accent: '#236B57',
  accentHover: '#195743',
  accentSoft: '#E8F1EC',
  positive: '#18794E',
  negative: '#B9413A',
  warning: '#A66A24',
  info: '#356B87',
  allocationPalette: [
    '#236B57', // Evergreen Accent
    '#356B87', // Information Teal/Blue
    '#A66A24', // Amber/Warm Gold
    '#18794E', // Positive Emerald
    '#5B5EA6', // Indigo/Slate Blue
    '#9E5A78', // Rose/Mauve
    '#4E79A7', // Steel Blue
    '#76B7B2', // Mint
  ],
};

const DARK_TOKENS: ChartThemeTokens = {
  isDark: true,
  grid: '#202D26',
  axis: '#AAB7AE',
  text: '#EEF4EF',
  muted: '#7F8D84',
  border: '#2B3931',
  tooltipBg: '#1B2620',
  tooltipBorder: '#2B3931',
  tooltipShadow: '0 6px 20px rgba(0, 0, 0, 0.35)',
  accent: '#4FA889',
  accentHover: '#65B99D',
  accentSoft: '#1C382E',
  positive: '#4CAF7D',
  negative: '#E16B63',
  warning: '#D6A25A',
  info: '#70A9C4',
  allocationPalette: [
    '#4FA889', // Evergreen Accent
    '#70A9C4', // Soft Blue
    '#D6A25A', // Warm Amber
    '#4CAF7D', // Sage/Positive Green
    '#8B80F9', // Violet
    '#E5889A', // Soft Coral
    '#5DA5DA', // Azure
    '#80CBC4', // Soft Mint
  ],
};

export function useChartTheme(): ChartThemeTokens {
  const { resolvedTheme } = useTheme();
  return useMemo(() => {
    return resolvedTheme === 'dark' ? DARK_TOKENS : LIGHT_TOKENS;
  }, [resolvedTheme]);
}
