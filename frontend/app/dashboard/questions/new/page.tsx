"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft } from "lucide-react";
import { coursesApi, questionsApi, type Course } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export default function NewQuestionPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    courseId: "",
    classId: "",
    lineUserId: "",
    questionText: "",
  });

  // 載入課程列表
  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    try {
      // 只載入已啟用的課程
      const courses = await coursesApi.getAll({ is_active: true });
      setCourses(courses);
    } catch (error) {
      console.error("載入課程失敗:", error);
      toast({
        title: "錯誤",
        description: "載入課程列表失敗",
        variant: "destructive",
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 驗證表單
    if (!formData.courseId) {
      toast({
        title: "錯誤",
        description: "請選擇課程",
        variant: "destructive",
      });
      return;
    }

    if (!formData.lineUserId) {
      toast({
        title: "錯誤",
        description: "請輸入學生 Line ID",
        variant: "destructive",
      });
      return;
    }

    if (!formData.questionText.trim()) {
      toast({
        title: "錯誤",
        description: "請輸入提問內容",
        variant: "destructive",
      });
      return;
    }

    try {
      setLoading(true);
      await questionsApi.create({
        course_id: formData.courseId,
        class_id: formData.classId || undefined,
        line_user_id: formData.lineUserId,
        question_text: formData.questionText,
      });

      toast({
        title: "成功",
        description: "提問已成功創建（已自動去識別化）",
      });
      router.push("/dashboard/questions");
    } catch (error) {
      console.error("創建提問失敗:", error);
      const errorMessage =
        error instanceof Error ? error.message : "創建提問失敗，請稍後再試";
      toast({
        title: "錯誤",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <Button variant="ghost" onClick={() => router.back()} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          返回
        </Button>
        <h1 className="text-4xl font-bold text-foreground mb-2">新增提問</h1>
        <p className="text-muted-foreground">
          創建新的學生提問（僅供測試使用）
        </p>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>提問資訊</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 課程選擇 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                課程 <span className="text-destructive">*</span>
              </label>
              <Select
                value={formData.courseId}
                onValueChange={(value) =>
                  setFormData({ ...formData, courseId: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="選擇課程" />
                </SelectTrigger>
                <SelectContent>
                  {courses.map((course) => (
                    <SelectItem key={course._id} value={course._id || ""}>
                      {course.course_name} ({course.course_code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 班級 ID（可選）*/}
            <div className="space-y-2">
              <label className="text-sm font-medium">班級 ID（選填）</label>
              <Input
                placeholder="例如：class_001"
                value={formData.classId}
                onChange={(e) =>
                  setFormData({ ...formData, classId: e.target.value })
                }
              />
              <p className="text-xs text-muted-foreground">
                如果提問屬於特定班級，可輸入班級 ID
              </p>
            </div>

            {/* Line User ID */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                學生 Line ID <span className="text-destructive">*</span>
              </label>
              <Input
                placeholder="例如：U1234567890abcdef"
                value={formData.lineUserId}
                onChange={(e) =>
                  setFormData({ ...formData, lineUserId: e.target.value })
                }
              />
              <p className="text-xs text-muted-foreground">
                此 ID 會自動使用 SHA256 進行去識別化處理
              </p>
            </div>

            {/* 提問內容 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                提問內容 <span className="text-destructive">*</span>
              </label>
              <Textarea
                placeholder="請輸入學生的提問內容..."
                value={formData.questionText}
                onChange={(e) =>
                  setFormData({ ...formData, questionText: e.target.value })
                }
                className="min-h-32"
              />
            </div>

            {/* 提示訊息 */}
            <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                <strong>注意：</strong>
                此功能僅供測試使用。在實際系統中，提問應該由學生透過 Line Bot
                提交，系統會自動進行去識別化處理。
              </p>
            </div>

            {/* 按鈕 */}
            <div className="flex gap-4">
              <Button type="submit" disabled={loading} className="flex-1">
                {loading ? "創建中..." : "創建提問"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
                className="flex-1"
              >
                取消
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
