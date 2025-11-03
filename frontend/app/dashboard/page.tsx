"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, MoreVertical, Trash2, Edit2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  questionsApi,
  coursesApi,
  type Question as ApiQuestion,
} from "@/lib/api";

interface Question {
  id: string;
  title: string;
  subject: string;
  status: "pending" | "reviewed" | "clustered";
  difficulty: "easy" | "medium" | "hard";
  date: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    router.push("/login");
    return null;
  }

  // 載入提問資料
  useEffect(() => {
    loadQuestions();
  }, []);

  const loadQuestions = async () => {
    try {
      setLoading(true);
      const questions = await questionsApi.getAll();
      // 獲取課程資料以顯示課程名稱
      const courses = await coursesApi.getAll();

      // 將後端資料轉換為前端格式
      const mappedQuestions: Question[] = questions.map((q: ApiQuestion) => {
        const course = courses.find((c) => c._id === q.course_id);

        // 狀態映射
        let status: "pending" | "reviewed" | "clustered" = "pending";
        if (q.status === "APPROVED") status = "reviewed";
        else if (q.cluster_id) status = "clustered";

        // 難度映射
        let difficulty: "easy" | "medium" | "hard" = "medium";
        if (q.ai_analysis?.difficulty_level === "EASY") difficulty = "easy";
        else if (
          q.ai_analysis?.difficulty_level === "HARD" ||
          q.ai_analysis?.difficulty_level === "VERY_HARD"
        )
          difficulty = "hard";

        return {
          id: q._id || "",
          title: q.question_text,
          subject: course?.course_name || "未知課程",
          status,
          difficulty,
          date: q.created_at
            ? new Date(q.created_at).toISOString().split("T")[0]
            : "",
        };
      });

      setQuestions(mappedQuestions);
    } catch (error) {
      console.error("載入提問失敗:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const filteredQuestions = questions.filter((question) => {
    const matchesSearch =
      question.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      question.subject.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      selectedStatus === "all" || question.status === selectedStatus;
    return matchesSearch && matchesStatus;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100";
      case "reviewed":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100";
      case "clustered":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100";
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case "easy":
        return "text-green-600 dark:text-green-400";
      case "medium":
        return "text-orange-600 dark:text-orange-400";
      case "hard":
        return "text-red-600 dark:text-red-400";
      default:
        return "text-gray-600";
    }
  };

  const stats = [
    { label: "總提問數", value: questions.length },
    {
      label: "待審核",
      value: questions.filter((q) => q.status === "pending").length,
    },
    {
      label: "已審核",
      value: questions.filter((q) => q.status === "reviewed").length,
    },
    {
      label: "已聚類",
      value: questions.filter((q) => q.status === "clustered").length,
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">儀表板</h1>
          <p className="text-muted-foreground">管理和審核您的教學提問</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {stats.map((stat) => (
            <Card key={stat.label} className="p-6">
              <p className="text-sm text-muted-foreground mb-2">{stat.label}</p>
              <p className="text-3xl font-bold text-primary">{stat.value}</p>
            </Card>
          ))}
        </div>

        {/* Questions Section */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-foreground">提問</h2>
            <Button
              onClick={() => router.push("/dashboard/questions/new")}
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              <Plus className="w-4 h-4 mr-2" />
              新增提問
            </Button>
          </div>

          {/* Search and Filters */}
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="搜尋提問..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-2">
              {["all", "pending", "reviewed", "clustered"].map((status) => (
                <Button
                  key={status}
                  variant={selectedStatus === status ? "default" : "outline"}
                  onClick={() => setSelectedStatus(status)}
                  className={
                    selectedStatus === status
                      ? "bg-primary text-primary-foreground"
                      : ""
                  }
                >
                  {status === "all"
                    ? "全部"
                    : status === "pending"
                    ? "待審核"
                    : status === "reviewed"
                    ? "已審核"
                    : "已聚類"}
                </Button>
              ))}
            </div>
          </div>

          {/* Questions List */}
          <div className="space-y-3">
            {loading ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">載入中...</p>
              </div>
            ) : filteredQuestions.length > 0 ? (
              filteredQuestions.map((question) => (
                <div
                  key={question.id}
                  className="p-4 border border-border rounded-lg hover:bg-secondary/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="font-semibold text-foreground mb-2">
                        {question.title}
                      </h3>
                      <div className="flex items-center gap-3 flex-wrap">
                        <Badge variant="outline">{question.subject}</Badge>
                        <Badge className={getStatusColor(question.status)}>
                          {question.status === "pending"
                            ? "待審核"
                            : question.status === "reviewed"
                            ? "已審核"
                            : "已聚類"}
                        </Badge>
                        <span
                          className={`text-sm font-medium ${getDifficultyColor(
                            question.difficulty
                          )}`}
                        >
                          {question.difficulty === "easy"
                            ? "簡單"
                            : question.difficulty === "medium"
                            ? "中等"
                            : "困難"}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {question.date}
                        </span>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>
                          <Edit2 className="w-4 h-4 mr-2" />
                          編輯提問
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-destructive">
                          <Trash2 className="w-4 h-4 mr-2" />
                          刪除
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12">
                <p className="text-muted-foreground">未找到提問</p>
              </div>
            )}
          </div>
        </Card>
      </main>
    </div>
  );
}
