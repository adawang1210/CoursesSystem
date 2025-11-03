"use client"

import type React from "react"

import { ThemeProvider } from "@/contexts/theme-context"

export function ThemeWrapper({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>
}
