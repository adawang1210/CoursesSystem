"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"

interface AuthContextType {
  isAuthenticated: boolean
  user: { username: string } | null
  login: (username: string, password: string) => Promise<boolean>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const COOKIE_NAME = "auth_session"
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7 // 7 days

function setCookie(name: string, value: string, maxAge: number) {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; SameSite=Lax`
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0`
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState<{ username: string } | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On mount, restore session from cookie
  useEffect(() => {
    try {
      const saved = getCookie(COOKIE_NAME)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed?.username) {
          setIsAuthenticated(true)
          setUser({ username: parsed.username })
        }
      }
    } catch {
      deleteCookie(COOKIE_NAME)
    }
    setIsLoading(false)
  }, [])

  const login = async (username: string, password: string): Promise<boolean> => {
    if (username === "admin" && password === "1234") {
      setIsAuthenticated(true)
      setUser({ username })
      setCookie(COOKIE_NAME, JSON.stringify({ username }), COOKIE_MAX_AGE)
      return true
    }
    return false
  }

  const logout = () => {
    setIsAuthenticated(false)
    setUser(null)
    deleteCookie(COOKIE_NAME)
  }

  // Don't render children until cookie check is done (prevents flash of login page)
  if (isLoading) {
    return null
  }

  return <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
