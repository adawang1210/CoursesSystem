"use client"

import { Button } from "@/components/ui/button"
import { LogOut, Settings, Moon, Sun } from "lucide-react"
import { useRouter } from "next/navigation"
import { useTheme } from "@/contexts/theme-context"

interface DashboardHeaderProps {
  user: { username: string } | null
  onLogout: () => void
}

export function DashboardHeader({ user, onLogout }: DashboardHeaderProps) {
  const router = useRouter()
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="border-b border-border bg-card">
      <div className="px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">TP</span>
          </div>
          <h1 className="text-xl font-bold text-foreground">AI 教學平台</h1>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-sm font-medium text-foreground">歡迎回來</p>
            <p className="text-xs text-muted-foreground">{user?.username}</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            title={theme === "light" ? "切換暗色模式" : "切換亮色模式"}
          >
            {theme === "light" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          </Button>
          <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard/settings")}>
            <Settings className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onLogout}
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </header>
  )
}
