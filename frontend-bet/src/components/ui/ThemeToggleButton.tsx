// src/components/ui/ThemeToggleButton.tsx
"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import Button from "@/components/ui/Button"; // Your existing Button component

// Simple Sun and Moon SVG Icons (or use an icon library like lucide-react)
const SunIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" stroke="currentColor"></path>
    <path d="M12 4v1M12 20v-1M4 12H3M21 12h-1M5.636 5.636l-.707-.707M19.071 19.071l-.707-.707M5.636 19.071l-.707.707M19.071 5.636l-.707.707" stroke="currentColor"></path>
  </svg>
);

const MoonIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" stroke="currentColor"></path>
  </svg>
);

export function ThemeToggleButton() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  // useEffect only runs on the client, so now we can safely show the UI
  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Render a placeholder or nothing until mounted to avoid hydration mismatch
    return <div className="h-10 w-10" />; // Or your Button's dimensions
  }

  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
      // Adjust colors for visibility on current navbar theme
      className="text-gray-600 dark:text-gray-400 hover:!bg-gray-100 dark:hover:!bg-gray-700 focus-visible:!ring-blue-500 dark:focus-visible:!ring-sky-500"
    >
      {resolvedTheme === "dark" ? (
        <SunIcon className="h-5 w-5" />
      ) : (
        <MoonIcon className="h-5 w-5" />
      )}
    </Button>
  );
}