"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  BookOpen, 
  MessageCircle, 
  Clock, 
  Sparkles,
  ArrowRight
} from "lucide-react";
import { coursesApi, qasApi, type Course, API_URL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [activeQAs, setActiveQAs] = useState<any[]>([]);
  const [aiModel, setAiModel] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 如果未登入則導向登入頁
  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const fetchDashboardData = async () => {
      setIsLoading(true);
      try {
        // 1. 取得課程數
        const coursesData = await coursesApi.getAll();
        setCourses(coursesData.filter((c) => c.is_active));

        // 2. 取得所有 Q&A 並過濾出「進行中」的任務
        const qasData = await qasApi.getAll();
        const now = new Date().getTime();
        
        const active = qasData.filter((qa: any) => {
          // 支援駝峰與底線命名防呆
          const allowReplies = qa.allow_replies ?? qa.allowReplies;
          const expiresAt = qa.expires_at ?? qa.expiresAt;
          
          if (!allowReplies) return false;
          if (!expiresAt) return true; // 不限時任務
          return new Date(expiresAt).getTime() > now;
        });
        
        setActiveQAs(active);

        // 3. 取得 AI 模型名稱
        try {
          const res = await fetch(`${API_URL}/health`);
          const health = await res.json();
          if (health.ai_model) setAiModel(health.ai_model);
        } catch {
          // 靜默失敗，保持顯示「隨時待命」
        }
      } catch (error) {
        console.error("載入儀表板資料失敗", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, [isAuthenticated]);

  if (!isAuthenticated) return null;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-foreground mb-2">
          歡迎回來，{user?.username || "老師"} 👋
        </h1>
        <p className="text-muted-foreground">這是您的教學任務總覽，隨時掌握學生的學習進度與課後互動。</p>
      </div>

      {/* 數據總覽 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-gradient-to-br from-indigo-50 to-white dark:from-indigo-950/20 dark:to-background border-indigo-100 dark:border-indigo-900">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400 mb-1">進行中的任務</p>
                <p className="text-4xl font-bold text-foreground">{isLoading ? "-" : activeQAs.length}</p>
              </div>
              <div className="p-3 bg-indigo-100 dark:bg-indigo-900/50 rounded-lg">
                <Clock className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">管理中的課程</p>
                <p className="text-4xl font-bold text-foreground">{isLoading ? "-" : courses.length}</p>
              </div>
              <div className="p-3 bg-secondary rounded-lg">
                <BookOpen className="w-6 h-6 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">AI 批閱大腦</p>
                <p className="text-lg font-bold text-foreground mt-2">隨時待命</p>
                {aiModel && (
                  <p className="text-xs text-muted-foreground mt-1">{aiModel}</p>
                )}
              </div>
              <div className="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                <Sparkles className="w-6 h-6 text-amber-600 dark:text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 進行中的任務列表 */}
      <Card className="shadow-sm border-border/50">
        <CardHeader className="flex flex-row items-center justify-between border-b pb-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-primary" />
            本週活躍 Q&A 任務
          </CardTitle>
          <Button variant="outline" size="sm" onClick={() => router.push('/dashboard/qa')}>
            管理所有任務 <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </CardHeader>
        <CardContent className="pt-6">
          {isLoading ? (
             <p className="text-center text-muted-foreground py-8">載入中...</p>
          ) : activeQAs.length > 0 ? (
            <div className="space-y-4">
              {activeQAs.map((qa) => {
                 const expiresAt = qa.expires_at ?? qa.expiresAt;
                 const isUnlimited = !expiresAt;
                 return (
                   <div key={qa._id || qa.id} className="flex items-center justify-between p-4 rounded-lg border bg-card hover:shadow-md transition-shadow">
                     <div className="flex-1 pr-4">
                       <h4 className="font-semibold text-base mb-1 line-clamp-1">{qa.question}</h4>
                       <p className="text-sm text-muted-foreground line-clamp-1">
                         {courses.find(c => c._id === qa.course_id)?.course_name || "未知課程"}
                       </p>
                     </div>
                     <div className="flex flex-col items-end gap-2 shrink-0">
                       <span className={`text-xs px-2 py-1 rounded-full border ${isUnlimited ? 'bg-green-50 text-green-600 border-green-200 dark:bg-green-900/20 dark:border-green-900' : 'bg-orange-50 text-orange-600 border-orange-200 dark:bg-orange-900/20 dark:border-orange-900 animate-pulse'}`}>
                         {isUnlimited ? '無限期進行中' : '限時倒數中'}
                       </span>
                       <Button size="sm" variant="ghost" className="h-8 text-indigo-600 dark:text-indigo-400" onClick={() => router.push('/dashboard/clustering')}>
                         前往批閱
                       </Button>
                     </div>
                   </div>
                 )
              })}
            </div>
          ) : (
            <div className="text-center py-12 bg-secondary/30 rounded-lg border-2 border-dashed">
              <MessageCircle className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-30" />
              <h3 className="text-base font-medium mb-1">目前沒有進行中的任務</h3>
              <p className="text-sm text-muted-foreground mb-4">發布課後問答任務，讓學生驗收本週學習成果</p>
              <Button onClick={() => router.push('/dashboard/qa')}>
                立即發布任務
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}