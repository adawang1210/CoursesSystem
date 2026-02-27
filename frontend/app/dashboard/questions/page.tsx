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
  RefreshCw, CheckCircle, XCircle, Trash2, 
  Bot, Sparkles, Copy, FileText, MessageCircle, Clock, CheckSquare, XSquare
} from "lucide-react";
import {
  questionsApi,
  coursesApi,
  type Question as ApiQuestion,
  type Course,
} from "@/lib/api";
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
  
  // AI 輔助視窗狀態
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<DisplayQuestion | null>(null);
  const [draftContent, setDraftContent] = useState("");
  const [isRegenerating, setIsRegenerating] = useState(false);

  const { toast } = useToast();

  useEffect(() => {
    loadCourses();
  }, []);

  useEffect(() => {
    if (courses.length > 0) {
      loadQuestions();
    }
  }, [courses, selectedCourse, selectedStatus]); 

  const loadCourses = async () => {
    try {
      const coursesData = await coursesApi.getAll();
      setCourses(coursesData);
    } catch (error) {
      console.error("載入課程失敗:", error);
    }
  };

  const loadQuestions = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (selectedCourse !== "all") params.course_id = selectedCourse;
      if (selectedStatus !== "all") params.status = selectedStatus.toUpperCase();

      const questionsData = await questionsApi.getAll(params);
      const filteredData = questionsData.filter(
        (q: ApiQuestion) => q.status !== "DELETED"
      );

      const mappedQuestions: DisplayQuestion[] = filteredData.map((q: any) => { 
          const course = courses.find((c) => c._id === q.course_id);
          return {
            id: q._id || "",
            courseId: q.course_id,
            courseName: course?.course_name || "未知課程",
            content: q.question_text,
            pseudonym: q.pseudonym ? q.pseudonym.substring(0, 8) + "..." : "匿名",
            status: q.status,
            difficulty: q.difficulty_level, 
            date: q.created_at ? new Date(q.created_at).toISOString().split("T")[0] : "",
            clusterId: q.cluster_id,
            keywords: q.keywords || [],
            aiResponseDraft: q.ai_response_draft,
            aiSummary: q.ai_summary
          };
      });
      setQuestions(mappedQuestions);
    } catch (error) {
      console.error("載入提問失敗:", error);
      toast({ title: "錯誤", description: "載入資料失敗", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  // 🔥 補齊：完整實作批准邏輯
  const handleApprove = async (id: string) => { 
    try {
      await questionsApi.updateStatus(id, { status: "APPROVED" });
      toast({ title: "成功", description: "提問已批准" });
      setQuestions(questions.map((q) => q.id === id ? { ...q, status: "APPROVED" } : q));
    } catch (error) {
      toast({ title: "錯誤", description: "更新失敗", variant: "destructive" });
    }
  };

  // 🔥 補齊：完整實作拒絕邏輯
  const handleReject = async (id: string) => { 
    try {
      await questionsApi.updateStatus(id, { status: "REJECTED" });
      toast({ title: "成功", description: "提問已拒絕" });
      setQuestions(questions.map((q) => q.id === id ? { ...q, status: "REJECTED" } : q));
    } catch (error) {
      toast({ title: "錯誤", description: "更新失敗", variant: "destructive" });
    }
  };

  const handleDelete = async (id: string) => { 
    try {
      await questionsApi.delete(id);
      toast({ title: "成功", description: "提問已刪除" });
      setQuestions(questions.filter((q) => q.id !== id));
    } catch (error) {
      toast({ title: "錯誤", description: "刪除失敗", variant: "destructive" });
    }
  };

  const openAiModal = (question: DisplayQuestion) => {
    setSelectedQuestion(question);
    setDraftContent(question.aiResponseDraft || "尚無草稿，請點擊重新生成...");
    setIsAiModalOpen(true);
  };

  const handleRegenerateDraft = async () => {
    if (!selectedQuestion) return;
    setIsRegenerating(true);
    
    try {
      const success = await aiApi.generateDraft(selectedQuestion.id);
      if (success) {
        toast({ title: "AI 思考中", description: "正在撰寫草稿，請稍候..." });
        
        let retryCount = 0;
        const maxRetries = 15;
        
        const pollInterval = setInterval(async () => {
          retryCount++;
          try {
            const updatedData = await aiApi.getQuestionAnalysis(selectedQuestion.id) as any;
            // 確保對應到攤平後的資料結構
            const newDraft = updatedData?.ai_response_draft;
            
            if (newDraft && newDraft !== selectedQuestion.aiResponseDraft) {
              clearInterval(pollInterval);
              setDraftContent(newDraft);
              
              setSelectedQuestion((prev) => prev ? { 
                ...prev, 
                aiResponseDraft: newDraft,
                aiSummary: updatedData.ai_summary || prev.aiSummary,
                difficulty: updatedData.difficulty_level || prev.difficulty,
                keywords: updatedData.keywords || prev.keywords
              } : null);

              setQuestions((prev) => prev.map(q => 
                q.id === selectedQuestion.id 
                  ? { 
                      ...q, 
                      aiResponseDraft: newDraft,
                      aiSummary: updatedData.ai_summary || q.aiSummary,
                      difficulty: updatedData.difficulty_level || q.difficulty,
                      keywords: updatedData.keywords || q.keywords
                    } 
                  : q
              ));

              setIsRegenerating(false);
              toast({ title: "生成完成", description: "AI 草稿已更新！" });
            } else if (retryCount >= maxRetries) {
              clearInterval(pollInterval);
              setIsRegenerating(false);
              toast({ title: "生成時間較長", description: "AI 還在背景運作中，請稍後手動刷新頁面查看。" });
            }
          } catch (err) {
            console.error("輪詢檢查失敗:", err);
          }
        }, 2000); 
      } else {
        setIsRegenerating(false);
        toast({ title: "錯誤", description: "無法啟動 AI 生成任務", variant: "destructive" });
      }
    } catch (error) {
      setIsRegenerating(false);
      toast({ title: "錯誤", description: "連線發生錯誤", variant: "destructive" });
    }
  };

  const copyDraft = () => {
    navigator.clipboard.writeText(draftContent);
    toast({ title: "已複製", description: "草稿已複製到剪貼簿" });
  };

  // 🔥 補齊：顏色判斷邏輯
  const getStatusColor = (status: string) => {
    switch (status?.toUpperCase()) {
      case "PENDING": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "APPROVED": return "bg-green-100 text-green-800 border-green-200";
      case "REJECTED": return "bg-red-100 text-red-800 border-red-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getDifficultyColor = (difficulty?: string) => {
    switch (difficulty?.toLowerCase()) {
      case "easy": return "text-green-600 border-green-200 bg-green-50";
      case "medium": return "text-yellow-600 border-yellow-200 bg-yellow-50";
      case "hard": return "text-red-600 border-red-200 bg-red-50";
      default: return "text-gray-600 border-gray-200 bg-gray-50";
    }
  };

  const filteredQuestions = questions.filter((question) =>
    question.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">提問管理</h1>
        <p className="text-muted-foreground">審核和管理學生提問與 AI 分析成果</p>
      </div>
      
      {/* 🔥 補齊：統計卡片區塊 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-full text-primary"><MessageCircle className="w-6 h-6" /></div>
            <div><p className="text-sm text-muted-foreground">總提問數</p><p className="text-2xl font-bold">{questions.length}</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 bg-yellow-500/10 rounded-full text-yellow-600"><Clock className="w-6 h-6" /></div>
            <div><p className="text-sm text-muted-foreground">待審核</p><p className="text-2xl font-bold">{questions.filter(q => q.status === "PENDING").length}</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 bg-green-500/10 rounded-full text-green-600"><CheckSquare className="w-6 h-6" /></div>
            <div><p className="text-sm text-muted-foreground">已批准</p><p className="text-2xl font-bold">{questions.filter(q => q.status === "APPROVED").length}</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 bg-red-500/10 rounded-full text-red-600"><XSquare className="w-6 h-6" /></div>
            <div><p className="text-sm text-muted-foreground">已拒絕</p><p className="text-2xl font-bold">{questions.filter(q => q.status === "REJECTED").length}</p></div>
          </CardContent>
        </Card>
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
                      <Badge className={getStatusColor(question.status)}>{question.status === "PENDING" ? "待處理" : question.status === "APPROVED" ? "已批准" : "已拒絕"}</Badge>
                      {question.difficulty && (
                        <Badge variant="outline" className={`uppercase ${getDifficultyColor(question.difficulty)}`}>
                          {question.difficulty}
                        </Badge>
                      )}
                      {question.aiSummary && (
                        <div className="flex items-center text-xs text-muted-foreground bg-secondary/50 px-2 py-1 rounded line-clamp-1 max-w-[300px]" title={question.aiSummary}>
                          <Bot className="w-3 h-3 mr-1 flex-shrink-0" />
                          <span className="truncate">{question.aiSummary}</span>
                        </div>
                      )}
                    </div>
                    
                    <h3 className="text-lg font-semibold mb-2">{question.content}</h3>
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{question.courseName}</span>
                      <span>提出者：{question.pseudonym}</span>
                      <span>{question.date}</span>
                    </div>

                    {question.keywords && question.keywords.length > 0 && (
                      <div className="flex gap-2 mt-3 flex-wrap">
                        {question.keywords.map((keyword, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">#{keyword}</Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
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
              <div className="space-y-2">
                <Label className="text-muted-foreground font-semibold">學生提問</Label>
                <div className="p-3 bg-secondary/20 rounded-md text-sm border">
                  {selectedQuestion.content}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-muted-foreground">難度評估</Label>
                  <div className="font-medium flex items-center gap-2">
                    <Badge variant="outline" className={`uppercase ${getDifficultyColor(selectedQuestion.difficulty)}`}>
                        {selectedQuestion.difficulty || "未分析"}
                    </Badge>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground">關鍵字</Label>
                  <div className="flex gap-1 flex-wrap">
                    {selectedQuestion.keywords?.map(k => (
                      <Badge key={k} variant="secondary" className="text-xs">#{k}</Badge>
                    )) || "無"}
                  </div>
                </div>
              </div>

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