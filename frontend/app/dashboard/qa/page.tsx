"use client";
import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Search,
  MessageCircle,
  Plus,
  Loader2,
  X,
  Trash2,
  Clock, 
  StopCircle, 
  Timer,
  RefreshCw,
  Zap 
} from "lucide-react";
import { qasApi, coursesApi, type Course } from "@/lib/api";
import { aiApi } from "@/lib/api/ai"; 
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/auth-context";
import { useRouter } from "next/navigation"; 

interface QAItem {
  id: string;
  question: string;
  answer: string;
  author: string;
  course: string;
  courseId: string;
  tags: string[];
  category?: string;
  isPublished: boolean;
  lastUpdated: string;
  allowReplies?: boolean;
  durationMinutes?: number;
  expiresAt?: string;
}

export default function QAPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  const router = useRouter(); 
  const [qaList, setQaList] = useState<QAItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedQA, setSelectedQA] = useState<QAItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [courses, setCourses] = useState<Map<string, string>>(new Map());
  const [courseList, setCourseList] = useState<Course[]>([]);

  const [qaReplies, setQaReplies] = useState<any[]>([]);
  const [isLoadingReplies, setIsLoadingReplies] = useState(false);
  const [isClustering, setIsClustering] = useState(false); 

  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  
  // =========== 🔥 修改 1：新增 is_time_limited 狀態 ===========
  const [newQA, setNewQA] = useState({
    course_id: "",
    question: "",
    answer: "",
    category: "",
    tags: [] as string[],
    is_published: true, 
    allow_replies: true, // 預設開啟回覆
    is_time_limited: false, // 預設不限時
    duration_minutes: 10080, // 預設一週
  });
  // =========================================================
  
  const [tagInput, setTagInput] = useState("");

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [qaToDelete, setQaToDelete] = useState<QAItem | null>(null);

  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editQA, setEditQA] = useState({
    id: "",
    course_id: "",
    question: "",
    answer: "",
    category: "",
    tags: [] as string[],
    is_published: false,
  });
  const [editTagInput, setEditTagInput] = useState("");

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await coursesApi.getAll();
        setCourseList(response);
        const courseMap = new Map<string, string>();
        response.forEach((course) => {
          if (course._id) {
            courseMap.set(course._id, course.course_name);
          }
        });
        setCourses(courseMap);
        if (response.length > 0 && response[0]._id) {
          setNewQA((prev) => ({ ...prev, course_id: response[0]._id || "" }));
        }
      } catch (error) {
        console.error("載入課程失敗:", error);
      }
    };
    fetchCourses();
  }, []);

  const transformQAs = useCallback((qas: any[]): QAItem[] => {
    const ensureUTC = (dateStr?: string) => {
      if (!dateStr) return undefined;
      return dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`;
    };

    return qas.map((qa: any) => ({
      id: qa._id || "",
      question: qa.question,
      answer: qa.answer,
      author: qa.created_by || "未知",
      course: courses.get(qa.course_id) || qa.course_id,
      courseId: qa.course_id,
      tags: qa.tags || [],
      category: qa.category,
      isPublished: qa.is_published || false,
      lastUpdated: qa.updated_at
        ? new Date(ensureUTC(qa.updated_at)!).toLocaleDateString("zh-TW")
        : new Date(ensureUTC(qa.created_at) || "").toLocaleDateString("zh-TW"),
      allowReplies: qa.allow_replies,
      durationMinutes: qa.duration_minutes,
      expiresAt: ensureUTC(qa.expires_at),
    }));
  }, [courses]);

  const fetchQAs = useCallback(async () => {
    try {
      setIsLoading(true);
      const qas = await qasApi.getAll();
      setQaList(transformQAs(qas));
    } catch (error) {
      toast({ variant: "destructive", title: "載入失敗", description: "無法載入 Q&A 資料" });
    } finally {
      setIsLoading(false);
    }
  }, [transformQAs, toast]);

  useEffect(() => {
    fetchQAs();
  }, [courses, fetchQAs]);

  const loadReplies = async (qaId: string) => {
    setIsLoadingReplies(true);
    try {
      const replies = await qasApi.getReplies(qaId);
      setQaReplies(replies);
    } catch (error) {
      console.error("載入回覆失敗", error);
    } finally {
      setIsLoadingReplies(false);
    }
  };

  useEffect(() => {
    if (selectedQA?.allowReplies) {
      loadReplies(selectedQA.id);
    } else {
      setQaReplies([]);
    }
  }, [selectedQA]);

  const handleRunAIClustering = async (qaId: string, courseId: string) => {
    setIsClustering(true);
    try {
      const success = await aiApi.runClustering(courseId, 5, qaId);
      if (success) {
        toast({
          title: "AI 批閱已啟動 ⚡",
          description: "正在背景批閱學生回答，請前往「AI 聚類」頁面查看結果！",
        });
        setTimeout(() => {
          router.push("/dashboard/clustering");
        }, 1500);
      } else {
        toast({ title: "啟動失敗", description: "無法啟動 AI 批閱任務", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "錯誤", description: "系統發生錯誤", variant: "destructive" });
    } finally {
      setIsClustering(false);
    }
  };

  const filteredQAs = qaList.filter(
    (item) =>
      item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateQA = async () => {
    if (!newQA.course_id) { toast({ variant: "destructive", title: "錯誤", description: "請選擇課程" }); return; }
    if (!newQA.question.trim()) { toast({ variant: "destructive", title: "錯誤", description: "請輸入問題" }); return; }
    if (!newQA.answer.trim()) { toast({ variant: "destructive", title: "錯誤", description: "請輸入答案" }); return; }

    try {
      setIsCreating(true);
      await qasApi.create({
        course_id: newQA.course_id,
        question: newQA.question.trim(),
        answer: newQA.answer.trim(),
        category: newQA.category.trim() || undefined,
        tags: newQA.tags.length > 0 ? newQA.tags : undefined,
        is_published: newQA.is_published,
        allow_replies: newQA.allow_replies,
        // =========== 🔥 修改 2：只有勾選限時，才送出 duration_minutes ===========
        duration_minutes: (newQA.allow_replies && newQA.is_time_limited) ? Number(newQA.duration_minutes) : undefined,
        // ======================================================================
        created_by: user?.username || "admin",
      });

      toast({ title: "成功", description: "Q&A 已新增" });

      setNewQA({
        course_id: courseList[0]?._id || "",
        question: "",
        answer: "",
        category: "",
        tags: [],
        is_published: true,
        allow_replies: true,
        is_time_limited: false,
        duration_minutes: 10080,
      });
      setTagInput("");
      setIsCreateDialogOpen(false);
      
      const qas = await qasApi.getAll();
      setQaList(transformQAs(qas));
    } catch (error: any) {
      toast({ variant: "destructive", title: "新增失敗", description: "無法新增 Q&A" });
    } finally {
      setIsCreating(false);
    }
  };

  const handleStopQA = async (id: string) => {
    try {
      await qasApi.stopQAReplies(id);
      toast({ title: "已結束", description: "已手動關閉此 Q&A 的回覆通道" });
      
      const qas = await qasApi.getAll();
      setQaList(transformQAs(qas));
      
      if (selectedQA?.id === id) {
        setSelectedQA(prev => prev ? { ...prev, allowReplies: false } : null);
      }
    } catch (error) {
      toast({ variant: "destructive", title: "錯誤", description: "無法結束 Q&A" });
    }
  };

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim();
    if (trimmedTag && !newQA.tags.includes(trimmedTag)) {
      setNewQA({ ...newQA, tags: [...newQA.tags, trimmedTag] });
      setTagInput("");
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setNewQA({ ...newQA, tags: newQA.tags.filter((tag) => tag !== tagToRemove) });
  };

  const handleOpenCreateDialog = () => {
    if (courseList.length === 0) {
      toast({ variant: "destructive", title: "無法新增", description: "請先建立課程" });
      return;
    }
    setNewQA(prev => ({ ...prev, course_id: courseList[0]?._id || "" }));
    setTagInput("");
    setIsCreateDialogOpen(true);
  };

  const handleOpenEditDialog = (qa: QAItem) => {
    setEditQA({
      id: qa.id,
      course_id: qa.courseId,
      question: qa.question,
      answer: qa.answer,
      category: qa.category || "",
      tags: qa.tags || [],
      is_published: qa.isPublished,
    });
    setEditTagInput("");
    setIsEditDialogOpen(true);
  };

  const handleEditQA = async () => {
    if (!editQA.question.trim() || !editQA.answer.trim()) {
      toast({ variant: "destructive", title: "錯誤", description: "請輸入完整內容" });
      return;
    }
    try {
      setIsEditing(true);
      await qasApi.update(editQA.id, {
        question: editQA.question.trim(),
        answer: editQA.answer.trim(),
        category: editQA.category.trim() || undefined,
        tags: editQA.tags.length > 0 ? editQA.tags : undefined,
        is_published: editQA.is_published,
      });
      toast({ title: "成功", description: "Q&A 已更新" });
      setIsEditDialogOpen(false);
      
      const qas = await qasApi.getAll();
      const transformed = transformQAs(qas);
      setQaList(transformed);
      
      if (selectedQA?.id === editQA.id) {
        const updatedQA = transformed.find((qa) => qa.id === editQA.id);
        if (updatedQA) setSelectedQA(updatedQA);
      }
    } catch (error) {
      toast({ variant: "destructive", title: "更新失敗", description: "無法更新 Q&A" });
    } finally {
      setIsEditing(false);
    }
  };

  const handleAddEditTag = () => {
    const trimmedTag = editTagInput.trim();
    if (trimmedTag && !editQA.tags.includes(trimmedTag)) {
      setEditQA({ ...editQA, tags: [...editQA.tags, trimmedTag] });
      setEditTagInput("");
    }
  };

  const handleRemoveEditTag = (tagToRemove: string) => {
    setEditQA({ ...editQA, tags: editQA.tags.filter((tag) => tag !== tagToRemove) });
  };

  const handleOpenDeleteDialog = (qa: QAItem) => {
    setQaToDelete(qa);
    setIsDeleteDialogOpen(true);
  };

  const handleDeleteQA = async () => {
    if (!qaToDelete) return;
    try {
      setIsDeleting(true);
      await qasApi.delete(qaToDelete.id);
      toast({ title: "成功", description: "Q&A 已刪除" });
      setIsDeleteDialogOpen(false);
      setQaToDelete(null);
      if (selectedQA?.id === qaToDelete.id) setSelectedQA(null);
      
      const qas = await qasApi.getAll();
      setQaList(transformQAs(qas));
    } catch (error) {
      toast({ variant: "destructive", title: "刪除失敗", description: "無法刪除 Q&A" });
    } finally {
      setIsDeleting(false);
    }
  };

  // =========== 🔥 修改 3：完美判斷不限時任務是否為 Active ===========
  const isQAActive = (qa: QAItem) => {
    if (!qa.allowReplies) return false;
    if (!qa.expiresAt) return true; // 如果允許回覆且沒有過期時間 = 進行中
    return new Date(qa.expiresAt).getTime() > now.getTime();
  };

  const formatTimeLeft = (expiresAt?: string) => {
    if (!expiresAt) return "不限時"; 
    const diff = new Date(expiresAt).getTime() - now.getTime();
    if (diff <= 0) return "已結束";
    const m = Math.floor(diff / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };
  // =================================================================

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-foreground mb-2">Q&A 管理</h1>
      <p className="text-muted-foreground mb-8">發布課後問答任務，並收集學生的回答</p>

      <div className="flex gap-4 items-center mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="搜尋問題..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
        </div>
        <Button className="whitespace-nowrap bg-indigo-600 hover:bg-indigo-700 text-white" onClick={handleOpenCreateDialog}>
          <Plus className="w-4 h-4 mr-2" />
          發布課後 Q&A 任務
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">載入中...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-3">
            {filteredQAs.length === 0 ? (
              <Card className="bg-secondary/30 border-dashed">
                <CardContent className="py-12 text-center">
                  <MessageCircle className="w-12 h-12 mx-auto text-muted-foreground mb-3 opacity-50" />
                  <p className="text-muted-foreground mb-4">
                    {searchQuery ? "找不到符合的 Q&A" : "目前沒有 Q&A 資料"}
                  </p>
                  {!searchQuery && (
                    <Button onClick={handleOpenCreateDialog}>
                      <Plus className="w-4 h-4 mr-2" />
                      建立第一個 Q&A 任務
                    </Button>
                  )}
                </CardContent>
              </Card>
            ) : (
              filteredQAs.map((qa) => (
                <Card key={qa.id} className={`cursor-pointer transition-all border-l-4 ${selectedQA?.id === qa.id ? 'border-l-indigo-600 shadow-md' : 'border-l-transparent hover:shadow-md'}`} onClick={() => setSelectedQA(qa)}>
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-semibold text-foreground flex-1">{qa.question}</h3>
                      <div className="flex items-center gap-2">
                        {/* 🔥 依照是否限時，顯示不同顏色的標籤 */}
                        {qa.allowReplies && isQAActive(qa) && qa.expiresAt && (
                          <span className="flex items-center text-xs bg-red-500 text-white px-2 py-1 rounded animate-pulse">
                            <Timer className="w-3 h-3 mr-1" />
                            {formatTimeLeft(qa.expiresAt)}
                          </span>
                        )}
                        {qa.allowReplies && isQAActive(qa) && !qa.expiresAt && (
                          <span className="flex items-center text-xs bg-green-500/10 text-green-600 border border-green-200 dark:border-green-900 px-2 py-1 rounded">
                            <Clock className="w-3 h-3 mr-1" />
                            任務進行中
                          </span>
                        )}
                        {(!qa.allowReplies || !isQAActive(qa)) && (
                          <span className="text-xs bg-gray-200 text-gray-600 px-2 py-1 rounded">已結束</span>
                        )}
                        {!qa.isPublished && (
                          <span className="text-xs bg-yellow-500/10 text-yellow-600 px-2 py-1 rounded">草稿</span>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{qa.answer}</p>
                    <div className="flex justify-between items-center text-xs">
                      <div className="flex gap-2 flex-wrap">
                        {qa.tags.slice(0, 3).map((tag, idx) => (
                          <span key={idx} className="bg-secondary text-secondary-foreground px-2 py-1 rounded">{tag}</span>
                        ))}
                      </div>
                      <span className="bg-primary/10 text-primary px-2 py-1 rounded">{qa.course}</span>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>

          <div className="lg:col-span-1">
            {selectedQA ? (
              <Card className="sticky top-8">
                <CardHeader>
                  <CardTitle className="text-lg">詳細信息</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {selectedQA.allowReplies && (
                     <div className={`p-4 rounded-lg border ${isQAActive(selectedQA) ? 'bg-indigo-50 border-indigo-100 dark:bg-indigo-950/20' : 'bg-secondary/50'}`}>
                        <div className="flex items-center justify-between mb-2">
                           <span className="font-semibold flex items-center text-sm">
                             <Clock className="w-4 h-4 mr-2" />
                             LINE 互動任務
                           </span>
                           <span className={`text-sm font-bold ${isQAActive(selectedQA) ? (selectedQA.expiresAt ? 'text-red-600' : 'text-green-600') : 'text-muted-foreground'}`}>
                             {isQAActive(selectedQA) ? (selectedQA.expiresAt ? formatTimeLeft(selectedQA.expiresAt) : "進行中 (不限時)") : "已關閉"}
                           </span>
                        </div>
                        {isQAActive(selectedQA) && (
                          <Button variant="destructive" size="sm" className="w-full mt-2" onClick={() => handleStopQA(selectedQA.id)}>
                            <StopCircle className="w-4 h-4 mr-2" /> 立即結束任務
                          </Button>
                        )}
                     </div>
                  )}

                  <div>
                    <p className="text-xs uppercase text-muted-foreground mb-1">問題</p>
                    <p className="font-medium text-sm p-3 bg-secondary/30 rounded-md">{selectedQA.question}</p>
                  </div>

                  {selectedQA.allowReplies && (
                    <div className="pt-2">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-xs uppercase font-bold text-indigo-600 flex items-center">
                          <MessageCircle className="w-3 h-3 mr-1" /> 
                          學生即時回覆 ({qaReplies.length})
                        </p>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800"
                            onClick={() => handleRunAIClustering(selectedQA.id, selectedQA.courseId)}
                            disabled={isClustering || qaReplies.length === 0}
                          >
                            {isClustering ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Zap className="w-3 h-3 mr-1" />}
                            AI 批閱
                          </Button>
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => loadReplies(selectedQA.id)}>
                            <RefreshCw className={`w-3 h-3 ${isLoadingReplies ? 'animate-spin' : ''}`} />
                          </Button>
                        </div>
                      </div>
                      
                      <div className="space-y-2 max-h-[250px] overflow-y-auto pr-1">
                        {isLoadingReplies && qaReplies.length === 0 ? (
                           <div className="text-center py-4"><Loader2 className="w-4 h-4 animate-spin mx-auto text-muted-foreground" /></div>
                        ) : qaReplies.length === 0 ? (
                           <p className="text-xs text-muted-foreground text-center py-4 border border-dashed rounded-md">尚無學生回覆</p>
                        ) : (
                           qaReplies.map(reply => {
                             const ensureUTC = (dateStr?: string) => dateStr ? (dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`) : undefined;
                             const replyTime = new Date(ensureUTC(reply.created_at) || reply.created_at);
                             return (
                               <div key={reply._id} className="p-3 bg-indigo-50 dark:bg-indigo-950/30 rounded-lg border border-indigo-100 dark:border-indigo-900">
                                  <div className="flex justify-between items-center mb-1">
                                     <span className="text-xs font-bold text-foreground">{reply.pseudonym}</span>
                                     <span className="text-[10px] text-muted-foreground">
                                       {replyTime.toLocaleTimeString('zh-TW', {hour: '2-digit', minute:'2-digit'})}
                                     </span>
                                  </div>
                                  <p className="text-sm text-foreground/80">{reply.question_text}</p>
                               </div>
                             );
                           })
                        )}
                      </div>
                    </div>
                  )}

                  <div className="pt-2 border-t mt-4">
                    <p className="text-xs uppercase text-muted-foreground mb-1">標準答案</p>
                    <p className="text-sm p-3 bg-secondary/30 rounded-md whitespace-pre-wrap">{selectedQA.answer}</p>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                    <div>
                      <p className="text-xs text-muted-foreground">狀態</p>
                      <span className={`text-xs px-2 py-1 rounded inline-block mt-1 ${selectedQA.isPublished ? "bg-green-500/10 text-green-600" : "bg-yellow-500/10 text-yellow-600"}`}>
                        {selectedQA.isPublished ? "已發布" : "草稿"}
                      </span>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">更新時間</p>
                      <p className="font-medium text-sm mt-1">{selectedQA.lastUpdated}</p>
                    </div>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Button className="flex-1" variant="outline" onClick={(e) => { e.stopPropagation(); handleOpenEditDialog(selectedQA); }}>編輯</Button>
                    <Button variant="destructive" className="flex-1" onClick={(e) => { e.stopPropagation(); handleOpenDeleteDialog(selectedQA); }}>
                      <Trash2 className="w-4 h-4 mr-2" /> 刪除
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="bg-secondary/30 border-dashed flex items-center justify-center min-h-96">
                <CardContent className="text-center">
                  <MessageCircle className="w-12 h-12 mx-auto text-muted-foreground mb-3 opacity-50" />
                  <p className="text-muted-foreground">選擇一個任務查看詳細信息</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* 新增 Q&A 對話框 */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>發布課後問答任務</DialogTitle>
            <DialogDescription>建立問題與標準答案，並開放學生透過 LINE 作答</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="course">課程 <span className="text-destructive">*</span></Label>
              <Select value={newQA.course_id} onValueChange={(value) => setNewQA({ ...newQA, course_id: value })}>
                <SelectTrigger id="course"><SelectValue placeholder="選擇課程" /></SelectTrigger>
                <SelectContent>
                  {courseList.map((course) => (
                    <SelectItem key={course._id} value={course._id || ""}>{course.course_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="question">問題 <span className="text-destructive">*</span></Label>
              <Textarea id="question" placeholder="輸入要考驗學生的問題..." value={newQA.question} onChange={(e) => setNewQA({ ...newQA, question: e.target.value })} rows={2} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="answer">標準答案 / 批閱基準 <span className="text-destructive">*</span></Label>
              <Textarea id="answer" placeholder="提供給 AI 作為批閱基準的標準答案..." value={newQA.answer} onChange={(e) => setNewQA({ ...newQA, answer: e.target.value })} rows={4} />
            </div>

            {/* 🔥 全新設計的互動設定區塊 */}
            <div className="p-4 border border-indigo-100 bg-indigo-50/50 dark:bg-indigo-950/20 dark:border-indigo-900 rounded-lg space-y-4">
               <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="text-indigo-700 dark:text-indigo-400 font-bold flex items-center">
                      <MessageCircle className="w-4 h-4 mr-2" /> 允許學生回覆
                    </Label>
                    <p className="text-sm text-muted-foreground">開啟後，學生可在 LINE 聊天室中輸入答案進行作答</p>
                  </div>
                  <Switch checked={newQA.allow_replies} onCheckedChange={(checked) => setNewQA({ ...newQA, allow_replies: checked })} />
               </div>
               
               {newQA.allow_replies && (
                  <div className="pt-4 border-t border-indigo-100 dark:border-indigo-900">
                    <div className="flex items-center justify-between mb-3">
                       <Label className="block">設定自動關閉時間 (限時任務)</Label>
                       <Switch checked={newQA.is_time_limited} onCheckedChange={(c) => setNewQA({ ...newQA, is_time_limited: c })} />
                    </div>
                    
                    {newQA.is_time_limited ? (
                        <div className="flex items-center gap-2">
                           <Input 
                             type="number" 
                             min="1" 
                             value={newQA.duration_minutes} 
                             onChange={(e) => setNewQA({ ...newQA, duration_minutes: Number(e.target.value) })}
                             className="w-32"
                           />
                           <span className="text-sm text-muted-foreground">分鐘後自動關閉</span>
                        </div>
                    ) : (
                        <div className="p-2 bg-white/50 dark:bg-black/20 rounded border border-dashed border-indigo-200">
                           <p className="text-xs text-indigo-600 dark:text-indigo-400 text-center">
                             ✨ 目前為<b>不限時模式</b>：學生可隨時作答，直到您手動點擊「立即結束任務」。
                           </p>
                        </div>
                    )}
                  </div>
               )}
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg mt-4">
              <div className="space-y-0.5">
                <Label htmlFor="publish">立即發布</Label>
                <p className="text-sm text-muted-foreground">發布後將立即透過 LINE 廣播給學生</p>
              </div>
              <Switch id="publish" checked={newQA.is_published} onCheckedChange={(checked) => setNewQA({ ...newQA, is_published: checked })} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)} disabled={isCreating}>取消</Button>
            <Button onClick={handleCreateQA} disabled={isCreating} className="bg-indigo-600 hover:bg-indigo-700 text-white">
              {isCreating ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />發布中...</> : "發布任務"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>編輯 Q&A</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>課程</Label>
              <div className="p-2 bg-secondary/50 rounded-md text-sm">{courses.get(editQA.course_id) || editQA.course_id}</div>
            </div>
            <div className="space-y-2">
              <Label>問題</Label>
              <Textarea value={editQA.question} onChange={(e) => setEditQA({ ...editQA, question: e.target.value })} rows={3} />
            </div>
            <div className="space-y-2">
              <Label>標準答案</Label>
              <Textarea value={editQA.answer} onChange={(e) => setEditQA({ ...editQA, answer: e.target.value })} rows={5} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>取消</Button>
            <Button onClick={handleEditQA}>{isEditing ? "更新中..." : "儲存變更"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>確認刪除</DialogTitle></DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteQA}>確認刪除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}