// src/components/providers/ThemeProvider.tsx
"use client"; // This component will use client-side features

import * as React from "react";
import {ThemeProvider as NextThemesProvider, ThemeProviderProps} from "next-themes";

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}