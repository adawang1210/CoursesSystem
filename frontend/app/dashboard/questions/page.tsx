"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, RefreshCw, CheckCircle, XCircle, Trash2 } from "lucide-react";
import {
  questionsApi,
  coursesApi,
  type Question as ApiQuestion,
  type Course,
} from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface DisplayQuestion {
  id: string;
  courseId: string;
  courseName: string;
  content: string;
  pseudonym: string;
  status: string;
  difficulty?: string;
  date: string;
  clusterId?: string;
  keywords?: string[];
}

export default function QuestionsPage() {
  const [questions, setQuestions] = useState<DisplayQuestion[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [selectedCourse, setSelectedCourse] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  // 載入課程和提問資料
  useEffect(() => {
    loadCourses();
    loadQuestions();
  }, [selectedCourse, selectedStatus]);

  const loadCourses = async () => {
    try {
      const courses = await coursesApi.getAll();
      setCourses(courses);
    } catch (error) {
      console.error("載入課程失敗:", error);
    }
  };

  const loadQuestions = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (selectedCourse !== "all") params.course_id = selectedCourse;
      if (selectedStatus !== "all")
        params.status = selectedStatus.toUpperCase();

      const questions = await questionsApi.getAll(params);
      // 過濾掉已刪除的提問
      const filteredData = questions.filter(
        (q: ApiQuestion) => q.status !== "DELETED"
      );

      const mappedQuestions: DisplayQuestion[] = filteredData.map(
        (q: ApiQuestion) => {
          const course = courses.find((c) => c._id === q.course_id);
          return {
            id: q._id || "",
            courseId: q.course_id,
            courseName: course?.course_name || "未知課程",
            content: q.question_text,
            pseudonym: q.pseudonym.substring(0, 8) + "...",
            status: q.status,
            difficulty: q.ai_analysis?.difficulty_level,
            date: q.created_at
              ? new Date(q.created_at).toISOString().split("T")[0]
              : "",
            clusterId: q.cluster_id,
            keywords: q.ai_analysis?.keywords || [],
          };
        }
      );
      setQuestions(mappedQuestions);
    } catch (error) {
      console.error("載入提問失敗:", error);
      toast({
        title: "錯誤",
        description: "載入提問資料失敗，請確認後端服務是否正常運行",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await questionsApi.updateStatus(id, { status: "APPROVED" });
      toast({
        title: "成功",
        description: "提問已批准",
      });
      loadQuestions();
    } catch (error) {
      console.error("批准提問失敗:", error);
      toast({
        title: "錯誤",
        description: "批准提問失敗",
        variant: "destructive",
      });
    }
  };

  const handleReject = async (id: string) => {
    try {
      await questionsApi.updateStatus(id, {
        status: "REJECTED",
        rejection_reason: "不符合提問標準",
      });
      toast({
        title: "成功",
        description: "提問已拒絕",
      });
      loadQuestions();
    } catch (error) {
      console.error("拒絕提問失敗:", error);
      toast({
        title: "錯誤",
        description: "拒絕提問失敗",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await questionsApi.delete(id);
      toast({
        title: "成功",
        description: "提問已刪除",
      });
      setQuestions(questions.filter((q) => q.id !== id));
    } catch (error) {
      console.error("刪除提問失敗:", error);
      toast({
        title: "錯誤",
        description: "刪除提問失敗",
        variant: "destructive",
      });
    }
  };

  const filteredQuestions = questions.filter((question) =>
    question.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case "PENDING":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100";
      case "APPROVED":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100";
      case "REJECTED":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100";
    }
  };

  const getDifficultyColor = (difficulty?: string) => {
    switch (difficulty) {
      case "EASY":
        return "text-green-600 dark:text-green-400";
      case "MEDIUM":
        return "text-orange-600 dark:text-orange-400";
      case "HARD":
      case "VERY_HARD":
        return "text-red-600 dark:text-red-400";
      default:
        return "text-gray-600";
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">提問管理</h1>
        <p className="text-muted-foreground">審核和管理學生提問</p>
      </div>

      {/* 篩選器 */}
      <div className="flex gap-4 mb-6 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <Input
            placeholder="搜尋提問內容..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full"
          />
        </div>
        <Select value={selectedCourse} onValueChange={setSelectedCourse}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="選擇課程" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有課程</SelectItem>
            {courses.map((course) => (
              <SelectItem key={course._id} value={course._id || ""}>
                {course.course_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={selectedStatus} onValueChange={setSelectedStatus}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="狀態" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有狀態</SelectItem>
            <SelectItem value="pending">待處理</SelectItem>
            <SelectItem value="approved">已批准</SelectItem>
            <SelectItem value="rejected">已拒絕</SelectItem>
          </SelectContent>
        </Select>
        <Button onClick={loadQuestions} variant="outline" size="icon">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* 統計卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              總提問數
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{questions.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              待處理
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {questions.filter((q) => q.status === "PENDING").length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              已批准
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {questions.filter((q) => q.status === "APPROVED").length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              已拒絕
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {questions.filter((q) => q.status === "REJECTED").length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 提問列表 */}
      {loading ? (
        <Card>
          <CardContent className="pt-12 pb-12 text-center">
            <p className="text-muted-foreground">載入中...</p>
          </CardContent>
        </Card>
      ) : filteredQuestions.length === 0 ? (
        <Card className="bg-secondary/30 border-dashed">
          <CardContent className="pt-12 pb-12 text-center">
            <p className="text-muted-foreground">沒有符合條件的提問</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredQuestions.map((question) => (
            <Card
              key={question.id}
              className="hover:shadow-md transition-shadow"
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge className={getStatusColor(question.status)}>
                        {question.status}
                      </Badge>
                      {question.difficulty && (
                        <Badge
                          variant="outline"
                          className={getDifficultyColor(question.difficulty)}
                        >
                          {question.difficulty}
                        </Badge>
                      )}
                      {question.clusterId && (
                        <Badge variant="outline">
                          群集: {question.clusterId}
                        </Badge>
                      )}
                    </div>
                    <h3 className="text-lg font-semibold mb-2">
                      {question.content}
                    </h3>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>課程: {question.courseName}</span>
                      <span>代號: {question.pseudonym}</span>
                      <span>日期: {question.date}</span>
                    </div>
                    {question.keywords && question.keywords.length > 0 && (
                      <div className="flex gap-2 mt-2">
                        {question.keywords.map((keyword, idx) => (
                          <Badge
                            key={idx}
                            variant="secondary"
                            className="text-xs"
                          >
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {question.status === "PENDING" && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleApprove(question.id)}
                          className="gap-2"
                        >
                          <CheckCircle className="h-4 w-4" />
                          批准
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleReject(question.id)}
                          className="gap-2 text-destructive"
                        >
                          <XCircle className="h-4 w-4" />
                          拒絕
                        </Button>
                      </>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleDelete(question.id)}
                      className="text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
