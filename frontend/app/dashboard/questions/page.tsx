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
// 🔥 新增 Dialog 相關元件與 Textarea
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { 
  Search, RefreshCw, CheckCircle, XCircle, Trash2, 
  Bot, Sparkles, Copy, FileText // 🔥 新增 icon
} from "lucide-react";
import {
  questionsApi,
  coursesApi,
  type Question as ApiQuestion,
  type Course,
} from "@/lib/api";
// 🔥 引入 aiApi
import { aiApi } from "@/lib/api/ai"; 
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
  // 🔥 新增 AI 欄位
  aiResponseDraft?: string;
  aiSummary?: string;
}

export default function QuestionsPage() {
  const [questions, setQuestions] = useState<DisplayQuestion[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [selectedCourse, setSelectedCourse] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  
  // 🔥 新增：控制 AI 輔助視窗的狀態
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<DisplayQuestion | null>(null);
  const [draftContent, setDraftContent] = useState("");
  const [isRegenerating, setIsRegenerating] = useState(false);

  const { toast } = useToast();

  // 1. 頁面初始化：只載入課程
  useEffect(() => {
    loadCourses();
  }, []);

  // 2. 當「課程列表」載入完成，或是「篩選條件」改變時，才去載入問題
  useEffect(() => {
    // 只有當課程列表有資料時，才去抓問題，這樣才能正確對應課程名稱
    if (courses.length > 0) {
      loadQuestions();
    }
  }, [courses, selectedCourse, selectedStatus]); 
  // ↑ 將 courses 加入依賴陣列，確保它是最新的

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
      const filteredData = questions.filter(
        (q: ApiQuestion) => q.status !== "DELETED"
      );

      const mappedQuestions: DisplayQuestion[] = filteredData.map(
        (q: any) => { // 暫時用 any 避免型別與後端不一致
          const course = courses.find((c) => c._id === q.course_id);
          // 🔥 修正資料映射：對應後端 schemas.py 的欄位
          return {
            id: q._id || "",
            courseId: q.course_id,
            courseName: course?.course_name || "未知課程",
            content: q.question_text,
            pseudonym: q.pseudonym.substring(0, 8) + "...",
            status: q.status,
            // 注意：後端 QuestionBase 直接包含這些欄位
            difficulty: q.difficulty_level, 
            date: q.created_at
              ? new Date(q.created_at).toISOString().split("T")[0]
              : "",
            clusterId: q.cluster_id,
            keywords: q.keywords || [],
            // 🔥 對應新的 AI 欄位
            aiResponseDraft: q.ai_response_draft,
            aiSummary: q.ai_summary
          };
        }
      );
      setQuestions(mappedQuestions);
    } catch (error) {
      console.error("載入提問失敗:", error);
      toast({ title: "錯誤", description: "載入資料失敗", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  // ... (handleApprove, handleReject, handleDelete 保持不變) ...
  const handleApprove = async (id: string) => { /* ...原程式碼... */ };
  const handleReject = async (id: string) => { /* ...原程式碼... */ };
  const handleDelete = async (id: string) => { 
    try {
      await questionsApi.delete(id);
      toast({ title: "成功", description: "提問已刪除" });
      setQuestions(questions.filter((q) => q.id !== id));
    } catch (error) {
      toast({ title: "錯誤", description: "刪除失敗", variant: "destructive" });
    }
  };

  // 🔥 新增：打開 AI 視窗
  const openAiModal = (question: DisplayQuestion) => {
    setSelectedQuestion(question);
    setDraftContent(question.aiResponseDraft || "尚無草稿，請點擊重新生成...");
    setIsAiModalOpen(true);
  };

  // 🔥 新增：重新生成草稿
  const handleRegenerateDraft = async () => {
    if (!selectedQuestion) return;
    setIsRegenerating(true);
    try {
      const success = await aiApi.generateDraft(selectedQuestion.id);
      if (success) {
        toast({ title: "成功", description: "AI 已重新生成草稿，請稍候刷新" });
        // 這裡簡單處理：重新載入列表 (實務上可以直接更新 state)
        await loadQuestions();
        // 嘗試更新當前視窗內容 (需從新列表中找回該問題)
        // 簡化：先關閉視窗讓使用者重開，或提示刷新
        setIsAiModalOpen(false); 
      } else {
        toast({ title: "錯誤", description: "生成失敗", variant: "destructive" });
      }
    } catch (error) {
      console.error(error);
    } finally {
      setIsRegenerating(false);
    }
  };

  // 🔥 新增：複製草稿
  const copyDraft = () => {
    navigator.clipboard.writeText(draftContent);
    toast({ title: "已複製", description: "草稿已複製到剪貼簿" });
  };

  const filteredQuestions = questions.filter((question) =>
    question.content.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  // ... (getStatusColor, getDifficultyColor 保持不變) ...
  const getStatusColor = (status: string) => { /* ...原程式碼... */ return "bg-gray-100"; };
  const getDifficultyColor = (difficulty?: string) => { /* ...原程式碼... */ return "text-gray-600"; };

  return (
    <div className="p-8">
      {/* ... (標題與篩選器區塊保持不變) ... */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">提問管理</h1>
        <p className="text-muted-foreground">審核和管理學生提問</p>
      </div>
      
      <div className="flex gap-4 mb-6 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <Input placeholder="搜尋提問內容..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
        </div>
        <Select value={selectedCourse} onValueChange={setSelectedCourse}>
          <SelectTrigger className="w-[200px]"><SelectValue placeholder="選擇課程" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有課程</SelectItem>
            {courses.map(c => <SelectItem key={c._id} value={c._id || ""}>{c.course_name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={selectedStatus} onValueChange={setSelectedStatus}>
          <SelectTrigger className="w-[150px]"><SelectValue placeholder="狀態" /></SelectTrigger>
          <SelectContent>
             <SelectItem value="all">所有狀態</SelectItem>
             <SelectItem value="pending">待處理</SelectItem>
             <SelectItem value="approved">已批准</SelectItem>
             <SelectItem value="rejected">已拒絕</SelectItem>
          </SelectContent>
        </Select>
        <Button onClick={loadQuestions} variant="outline" size="icon"><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {/* ... (統計卡片區塊保持不變) ... */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
         {/* ... (省略統計卡片代碼，保持原樣) ... */}
      </div>

      {/* 提問列表 */}
      {loading ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">載入中...</CardContent></Card>
      ) : filteredQuestions.length === 0 ? (
        <Card className="bg-secondary/30 border-dashed"><CardContent className="py-12 text-center text-muted-foreground">沒有符合條件的提問</CardContent></Card>
      ) : (
        <div className="space-y-4">
          {filteredQuestions.map((question) => (
            <Card key={question.id} className="hover:shadow-md transition-shadow group">
              <CardContent className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge className={getStatusColor(question.status)}>{question.status}</Badge>
                      {/* 難度標籤 */}
                      {question.difficulty && (
                        <Badge variant="outline" className={getDifficultyColor(question.difficulty)}>
                          {question.difficulty}
                        </Badge>
                      )}
                      {/* AI 摘要標籤 (如果有) */}
                      {question.aiSummary && (
                        <div className="flex items-center text-xs text-muted-foreground bg-secondary/50 px-2 py-1 rounded">
                          <Bot className="w-3 h-3 mr-1" />
                          {question.aiSummary}
                        </div>
                      )}
                    </div>
                    
                    <h3 className="text-lg font-semibold mb-2">{question.content}</h3>
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{question.courseName}</span>
                      <span>{question.pseudonym}</span>
                      <span>{question.date}</span>
                    </div>

                    {/* 關鍵字 */}
                    {question.keywords && question.keywords.length > 0 && (
                      <div className="flex gap-2 mt-3">
                        {question.keywords.map((keyword, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">#{keyword}</Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
                    {/* 🔥 新增：AI 擬答按鈕 */}
                    <Button 
                      size="sm" 
                      variant="default" 
                      className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white"
                      onClick={() => openAiModal(question)}
                    >
                      <Sparkles className="h-4 w-4" />
                      AI 擬答
                    </Button>

                    <div className="flex gap-2">
                      {question.status === "PENDING" && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => handleApprove(question.id)} title="批准">
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => handleReject(question.id)} title="拒絕">
                            <XCircle className="h-4 w-4 text-red-600" />
                          </Button>
                        </>
                      )}
                      <Button size="sm" variant="outline" onClick={() => handleDelete(question.id)} title="刪除">
                        <Trash2 className="h-4 w-4 text-gray-500" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 🔥 新增：AI 輔助視窗 (Dialog) */}
      <Dialog open={isAiModalOpen} onOpenChange={setIsAiModalOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-indigo-600" />
              AI 智慧輔助
            </DialogTitle>
            <DialogDescription>
              檢視 AI 對此問題的分析與建議回覆草稿
            </DialogDescription>
          </DialogHeader>

          {selectedQuestion && (
            <div className="grid gap-6 py-4">
              {/* 原始問題 */}
              <div className="space-y-2">
                <Label className="text-muted-foreground font-semibold">學生提問</Label>
                <div className="p-3 bg-secondary/20 rounded-md text-sm border">
                  {selectedQuestion.content}
                </div>
              </div>

              {/* AI 分析資訊 */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-muted-foreground">難度評估</Label>
                  <div className="font-medium flex items-center gap-2">
                    {selectedQuestion.difficulty || "未分析"}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground">關鍵字</Label>
                  <div className="flex gap-1 flex-wrap">
                    {selectedQuestion.keywords?.map(k => (
                      <Badge key={k} variant="secondary" className="text-xs">{k}</Badge>
                    )) || "無"}
                  </div>
                </div>
              </div>

              {/* 回覆草稿區 */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label className="text-indigo-600 font-semibold flex items-center gap-2">
                    <Sparkles className="w-3 h-3" /> 建議回覆草稿
                  </Label>
                  <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={copyDraft}>
                    <Copy className="w-3 h-3 mr-1" /> 複製
                  </Button>
                </div>
                <Textarea 
                  value={draftContent} 
                  onChange={(e) => setDraftContent(e.target.value)}
                  className="min-h-[200px] font-mono text-sm leading-relaxed"
                />
              </div>
            </div>
          )}

          <DialogFooter className="gap-2 sm:justify-between">
             <Button variant="ghost" onClick={() => setIsAiModalOpen(false)}>關閉</Button>
             <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  onClick={handleRegenerateDraft} 
                  disabled={isRegenerating}
                  className="gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${isRegenerating ? 'animate-spin' : ''}`} />
                  重新生成
                </Button>
                {/* 預留功能：直接採納草稿並發布 */}
                <Button onClick={() => { copyDraft(); setIsAiModalOpen(false); }}>
                  <FileText className="w-4 h-4 mr-2" />
                  複製並使用
                </Button>
             </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}