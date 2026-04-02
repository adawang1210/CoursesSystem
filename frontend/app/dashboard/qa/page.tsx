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
import { Checkbox } from "@/components/ui/checkbox";
import {
  Search,
  MessageCircle,
  Plus,
  Loader2,
  Trash2,
  Clock, 
  StopCircle, 
  Timer,
  RefreshCw,
  Zap,
  CheckCircle2, 
  XCircle,
  RotateCcw,     
  AlertTriangle,
  Target, 
  Lightbulb,
  Hash 
} from "lucide-react";
import { qasApi, coursesApi, questionsApi, type Course } from "@/lib/api";
import { aiApi } from "@/lib/api/ai"; 
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/auth-context";

interface QAItem {
  id: string;
  question: string;
  coreConcept: string;           
  expectedMisconceptions?: string; 
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
  maxAttempts?: number;
}

export default function QAPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  const [qaList, setQaList] = useState<QAItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedQA, setSelectedQA] = useState<QAItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [courses, setCourses] = useState<Map<string, string>>(new Map());
  const [courseList, setCourseList] = useState<Course[]>([]);

  const [qaReplies, setQaReplies] = useState<any[]>([]);
  const [isLoadingReplies, setIsLoadingReplies] = useState(false);
  const [isClustering, setIsClustering] = useState(false); 
  
  const [selectedReplyIds, setSelectedReplyIds] = useState<string[]>([]);

  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  
  const [newQA, setNewQA] = useState({
    course_id: "",
    question: "",
    core_concept: "", 
    expected_misconceptions: "", 
    category: "",
    tags: [] as string[],
    is_published: true, 
    allow_replies: true, 
    is_time_limited: false, 
    duration_minutes: 10080, 
    max_attempts: 1,
  });
  
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
    core_concept: "",
    expected_misconceptions: "",
    category: "",
    tags: [] as string[],
    is_published: false,
    max_attempts: 1,
  });
  
  const [editTagInput, setEditTagInput] = useState("");

  const [isReviewDialogOpen, setIsReviewDialogOpen] = useState(false);
  const [reviewingReply, setReviewingReply] = useState<any>(null);
  const [reviewStatus, setReviewStatus] = useState<"pending" | "approved" | "rejected">("pending");
  const [reviewFeedback, setReviewFeedback] = useState("");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  
  const [isReclusterDialogOpen, setIsReclusterDialogOpen] = useState(false);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await coursesApi.getAll({ is_active: true });
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
      coreConcept: qa.core_concept || qa.answer || "", 
      expectedMisconceptions: qa.expected_misconceptions || "",
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
      maxAttempts: qa.max_attempts !== undefined ? qa.max_attempts : 1,
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
    setSelectedReplyIds([]);
    if (selectedQA?.allowReplies) {
      loadReplies(selectedQA.id);
    } else {
      setQaReplies([]);
    }
  }, [selectedQA]);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedReplyIds(qaReplies.map(r => r._id));
    } else {
      setSelectedReplyIds([]);
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedReplyIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleBatchReview = async (status: "approved" | "rejected") => {
    if (selectedReplyIds.length === 0) return;
    try {
      setIsSubmittingReview(true);
      await questionsApi.batchUpdateReviewStatus({
        question_ids: selectedReplyIds,
        review_status: status
      });
      toast({ title: `成功批量${status === 'approved' ? '通過' : '退回'} ${selectedReplyIds.length} 筆回答！` });
      
      setSelectedReplyIds([]);
      if (selectedQA) loadReplies(selectedQA.id);
    } catch (error) {
      toast({ title: "批量操作失敗", variant: "destructive" });
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const handleRunAIClustering = async (qaId: string, courseId: string) => {
    if (unclusteredApprovedCount === 0) {
      const approvedCount = qaReplies.filter(r => r.review_status === 'approved').length;
      if (approvedCount === 0) {
        toast({
          title: "尚無可分析的作答",
          description: "請先將至少一筆學生作答批閱為「通過」，AI 才能進行診斷分析。",
          variant: "destructive",
        });
      } else {
        toast({
          title: "所有作答皆已診斷",
          description: "目前沒有新的未診斷作答，可前往「AI 聚類」頁面查看現有結果。",
        });
      }
      return;
    }

    setIsClustering(true);
    try {
      const success = await aiApi.runClustering(courseId, 5, qaId);
      if (success) {
        toast({
          title: "AI 批閱完成 ⚡",
          description: "診斷結果已更新，可前往「AI 聚類」頁面查看詳細分群。",
        });
        loadReplies(qaId);
      } else {
        toast({ title: "啟動失敗", description: "無法啟動 AI 批閱任務", variant: "destructive" });
      }
    } catch (error: any) {
      const detail = error?.message || "系統發生錯誤";
      const isQuota = detail.includes("配額") || detail.includes("quota");
      toast({
        title: isQuota ? "AI 配額已用盡" : "錯誤",
        description: isQuota ? "Gemini API 免費額度已耗盡，請稍後再試或升級為付費方案。" : detail,
        variant: "destructive",
      });
    } finally {
      setIsClustering(false);
    }
  };

  const handleRunReclustering = async () => {
    if (!selectedQA) return;
    setIsReclusterDialogOpen(false);
    setIsClustering(true);
    try {
      const success = await aiApi.runClustering(selectedQA.courseId, 5, selectedQA.id, true);
      if (success) {
        toast({
          title: "重新批閱完成 ⚡",
          description: "已全面重新診斷所有已通過的回答，可前往「AI 聚類」頁面查看詳細分群。",
        });
        loadReplies(selectedQA.id);
      } else {
        toast({ title: "啟動失敗", description: "無法啟動 AI 批閱任務", variant: "destructive" });
      }
    } catch (error: any) {
      const detail = error?.message || "系統發生錯誤";
      const isQuota = detail.includes("配額") || detail.includes("quota");
      toast({
        title: isQuota ? "AI 配額已用盡" : "錯誤",
        description: isQuota ? "Gemini API 免費額度已耗盡，請稍後再試或升級為付費方案。" : detail,
        variant: "destructive",
      });
    } finally {
      setIsClustering(false);
    }
  };

  const filteredQAs = qaList.filter(
    (item) =>
      item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.coreConcept.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateQA = async () => {
    if (!newQA.course_id) { toast({ variant: "destructive", title: "錯誤", description: "請選擇課程" }); return; }
    if (!newQA.question.trim()) { toast({ variant: "destructive", title: "錯誤", description: "請輸入問題" }); return; }
    if (!newQA.core_concept.trim()) { toast({ variant: "destructive", title: "錯誤", description: "請輸入核心觀念" }); return; }

    try {
      setIsCreating(true);
      await qasApi.create({
        course_id: newQA.course_id,
        question: newQA.question.trim(),
        core_concept: newQA.core_concept.trim(),
        expected_misconceptions: newQA.expected_misconceptions.trim() || undefined,
        category: newQA.category.trim() || undefined,
        tags: newQA.tags.length > 0 ? newQA.tags : undefined,
        is_published: newQA.is_published,
        allow_replies: newQA.allow_replies,
        duration_minutes: (newQA.allow_replies && newQA.is_time_limited) ? Number(newQA.duration_minutes) : undefined,
        max_attempts: Number(newQA.max_attempts),
        created_by: user?.username || "admin",
      } as any);

      toast({ title: "成功", description: "Q&A 任務已發布" });

      setNewQA({
        course_id: courseList[0]?._id || "",
        question: "",
        core_concept: "",
        expected_misconceptions: "",
        category: "",
        tags: [],
        is_published: true,
        allow_replies: true,
        is_time_limited: false,
        duration_minutes: 10080,
        max_attempts: 1, 
      });
      setTagInput("");
      setIsCreateDialogOpen(false);
      
      const qas = await qasApi.getAll();
      setQaList(transformQAs(qas));
    } catch (error: any) {
      toast({ variant: "destructive", title: "發布失敗", description: "無法新增 Q&A" });
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
      core_concept: qa.coreConcept,
      expected_misconceptions: qa.expectedMisconceptions || "",
      category: qa.category || "",
      tags: qa.tags || [],
      is_published: qa.isPublished,
      max_attempts: qa.maxAttempts !== undefined ? qa.maxAttempts : 1,
    });
    setEditTagInput("");
    setIsEditDialogOpen(true);
  };

  const handleEditQA = async () => {
    if (!editQA.question.trim() || !editQA.core_concept.trim()) {
      toast({ variant: "destructive", title: "無法儲存", description: "「老師的提問」與「期望的核心觀念」為必填欄位，不可為空白喔！" });
      return;
    }
    try {
      setIsEditing(true);
      await qasApi.update(editQA.id, {
        question: editQA.question.trim(),
        core_concept: editQA.core_concept.trim(),
        expected_misconceptions: editQA.expected_misconceptions.trim() || undefined,
        category: editQA.category.trim() || undefined,
        tags: editQA.tags.length > 0 ? editQA.tags : undefined,
        is_published: editQA.is_published,
        max_attempts: Number(editQA.max_attempts), 
      } as any);
      toast({ title: "成功", description: "Q&A 任務已更新" });
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

  const isQAActive = (qa: QAItem) => {
    if (!qa.allowReplies) return false;
    if (!qa.expiresAt) return true; 
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

  const handleOpenReviewDialog = (reply: any) => {
    setReviewingReply(reply);
    setReviewStatus(reply.review_status || "pending");
    setReviewFeedback(reply.feedback || "");
    setIsReviewDialogOpen(true);
  };

  const handleSubmitReview = async () => {
    if (!reviewingReply) return;
    try {
      setIsSubmittingReview(true);
      await questionsApi.updateReviewStatus(reviewingReply._id, {
        review_status: reviewStatus,
        feedback: reviewFeedback.trim()
      });
      toast({ title: "批閱儲存成功" });
      setIsReviewDialogOpen(false);
      if (selectedQA) loadReplies(selectedQA.id);
    } catch (error) {
      toast({ title: "批閱失敗", variant: "destructive" });
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const unclusteredApprovedCount = qaReplies.filter(r => r.review_status === 'approved' && !r.cluster_id).length;
  const hasClusteredReplies = qaReplies.some(r => !!r.cluster_id);

  const [replyFilter, setReplyFilter] = useState<"all" | "pending" | "approved" | "rejected">("all");
  const [expandedReplyId, setExpandedReplyId] = useState<string | null>(null);
  const filteredReplies = replyFilter === "all" ? qaReplies : qaReplies.filter(r => (r.review_status || "pending") === replyFilter);

  return (
    <div className="p-6 h-[calc(100vh-64px)] flex flex-col">
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Q&A 任務管理</h1>
          <p className="text-sm text-muted-foreground mt-1">發布課後診斷任務，探測學生的理解狀態與迷思概念</p>
        </div>
        <div className="flex gap-3 items-center">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="搜尋問題或觀念..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10 h-9" />
          </div>
          <Button className="whitespace-nowrap bg-indigo-600 hover:bg-indigo-700 text-white h-9" onClick={handleOpenCreateDialog}>
            <Plus className="w-4 h-4 mr-1" /> 發布診斷任務
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center flex-1">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">載入中...</span>
        </div>
      ) : (
        <div className="flex gap-4 flex-1 min-h-0">
          <div className="w-[280px] shrink-0 overflow-y-auto space-y-2 pr-1">
            {filteredQAs.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <MessageCircle className="w-10 h-10 mx-auto mb-2 opacity-40" />
                <p className="text-sm">{searchQuery ? "找不到符合的 Q&A" : "尚無診斷任務"}</p>
                {!searchQuery && <Button size="sm" className="mt-3" onClick={handleOpenCreateDialog}><Plus className="w-3 h-3 mr-1" />建立任務</Button>}
              </div>
            ) : (
              filteredQAs.map((qa) => (
                <div key={qa.id} onClick={() => setSelectedQA(qa)} className={`p-3 rounded-lg border cursor-pointer transition-all ${selectedQA?.id === qa.id ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20 shadow-sm' : 'border-border hover:border-indigo-300 hover:shadow-sm'}`}>
                  <p className="text-sm font-medium line-clamp-2 mb-1.5">{qa.question}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] bg-primary/10 text-primary px-1.5 py-0.5 rounded truncate max-w-[120px]">{qa.course}</span>
                    {qa.allowReplies && isQAActive(qa) ? (
                      <span className="text-[10px] bg-green-500/10 text-green-600 px-1.5 py-0.5 rounded">進行中</span>
                    ) : (
                      <span className="text-[10px] bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded">已結束</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="flex-1 flex flex-col min-h-0 min-w-0">
            {selectedQA ? (
              <>
                <div className="shrink-0 border rounded-lg p-4 mb-3 bg-card">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <h2 className="text-base font-semibold truncate">{selectedQA.question}</h2>
                        {selectedQA.allowReplies && isQAActive(selectedQA) ? (
                          selectedQA.expiresAt ? (
                            <span className="flex items-center text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded animate-pulse whitespace-nowrap shrink-0"><Timer className="w-3 h-3 mr-0.5" />{formatTimeLeft(selectedQA.expiresAt)}</span>
                          ) : (
                            <span className="text-[10px] bg-green-500/10 text-green-600 border border-green-200 dark:border-green-900 px-1.5 py-0.5 rounded whitespace-nowrap shrink-0">進行中</span>
                          )
                        ) : (
                          <span className="text-[10px] bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded whitespace-nowrap shrink-0">已結束</span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <p className="text-[10px] uppercase font-bold text-indigo-600 flex items-center mb-0.5"><Target className="w-3 h-3 mr-0.5" />核心觀念</p>
                          <p className="text-xs text-foreground/80 line-clamp-2">{selectedQA.coreConcept}</p>
                        </div>
                        {selectedQA.expectedMisconceptions && (
                          <div>
                            <p className="text-[10px] uppercase font-bold text-orange-600 flex items-center mb-0.5"><Lightbulb className="w-3 h-3 mr-0.5" />探測迷思</p>
                            <p className="text-xs text-foreground/80 line-clamp-2">{selectedQA.expectedMisconceptions}</p>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col gap-1.5 shrink-0">
                      <Button size="sm" variant="outline" className="h-7 text-xs" onClick={(e) => { e.stopPropagation(); handleOpenEditDialog(selectedQA); }}>編輯</Button>
                      {isQAActive(selectedQA) && <Button size="sm" variant="destructive" className="h-7 text-xs" onClick={() => handleStopQA(selectedQA.id)}><StopCircle className="w-3 h-3 mr-1" />結束</Button>}
                      <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive hover:text-destructive" onClick={(e) => { e.stopPropagation(); handleOpenDeleteDialog(selectedQA); }}><Trash2 className="w-3 h-3 mr-1" />刪除</Button>
                    </div>
                  </div>
                </div>

                {selectedQA.allowReplies ? (
                  <div className="flex-1 flex flex-col min-h-0 border rounded-lg bg-card">
                    <div className="shrink-0 p-3 border-b">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-semibold flex items-center"><MessageCircle className="w-4 h-4 mr-1.5 text-indigo-600" />學生作答 ({qaReplies.length})</p>
                        <div className="flex items-center gap-1">
                          {hasClusteredReplies ? (
                            <>
                              <Button variant="outline" size="sm" className="h-7 text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800" onClick={() => handleRunAIClustering(selectedQA.id, selectedQA.courseId)} disabled={isClustering}>
                                {isClustering ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Zap className="w-3 h-3 mr-1" />}AI 診斷 ({unclusteredApprovedCount})
                              </Button>
                              <Button variant="outline" size="sm" className="h-7 text-xs text-orange-600 border-orange-200 hover:bg-orange-50 dark:bg-orange-950/30 dark:border-orange-900" onClick={() => setIsReclusterDialogOpen(true)} disabled={isClustering}>
                                <RotateCcw className={`w-3 h-3 mr-1 ${isClustering ? 'animate-spin' : ''}`} />重新診斷
                              </Button>
                            </>
                          ) : (
                            <Button variant="outline" size="sm" className="h-7 text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800" onClick={() => handleRunAIClustering(selectedQA.id, selectedQA.courseId)} disabled={isClustering}>
                              {isClustering ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Zap className="w-3 h-3 mr-1" />}AI 診斷分析
                            </Button>
                          )}
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => loadReplies(selectedQA.id)}><RefreshCw className={`w-3 h-3 ${isLoadingReplies ? 'animate-spin' : ''}`} /></Button>
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex gap-1">
                          {(["all", "pending", "approved", "rejected"] as const).map(f => (
                            <Button key={f} variant={replyFilter === f ? "default" : "ghost"} size="sm" className={`h-6 text-[11px] px-2 ${replyFilter === f ? 'bg-indigo-600 text-white hover:bg-indigo-700' : ''}`} onClick={() => setReplyFilter(f)}>
                              {f === "all" ? `全部 (${qaReplies.length})` : f === "pending" ? `待批閱 (${qaReplies.filter(r => (r.review_status || "pending") === "pending").length})` : f === "approved" ? `通過 (${qaReplies.filter(r => r.review_status === "approved").length})` : `退回 (${qaReplies.filter(r => r.review_status === "rejected").length})`}
                            </Button>
                          ))}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Checkbox id="select-all-v2" checked={selectedReplyIds.length === filteredReplies.length && filteredReplies.length > 0} onCheckedChange={(c) => { if (c) { setSelectedReplyIds(filteredReplies.map(r => r._id)); } else { setSelectedReplyIds([]); } }} />
                          <Label htmlFor="select-all-v2" className="text-[11px] cursor-pointer select-none">全選</Label>
                          {selectedReplyIds.length > 0 && (
                            <>
                              <span className="text-[11px] text-muted-foreground">({selectedReplyIds.length})</span>
                              <Button variant="outline" size="sm" className="h-6 text-[11px] px-2 bg-green-50 text-green-700 hover:bg-green-100 border-green-200 dark:bg-green-900/30 dark:text-green-400" onClick={() => handleBatchReview("approved")} disabled={isSubmittingReview}><CheckCircle2 className="w-3 h-3 mr-0.5" />通過</Button>
                              <Button variant="outline" size="sm" className="h-6 text-[11px] px-2 bg-red-50 text-red-700 hover:bg-red-100 border-red-200 dark:bg-red-900/30 dark:text-red-400" onClick={() => handleBatchReview("rejected")} disabled={isSubmittingReview}><XCircle className="w-3 h-3 mr-0.5" />退回</Button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-3 space-y-2">
                      {isLoadingReplies && qaReplies.length === 0 ? (
                        <div className="text-center py-8"><Loader2 className="w-5 h-5 animate-spin mx-auto text-muted-foreground" /></div>
                      ) : filteredReplies.length === 0 ? (
                        <p className="text-xs text-muted-foreground text-center py-8 border border-dashed rounded-md">{qaReplies.length === 0 ? "尚無學生回覆" : "此篩選條件下無回覆"}</p>
                      ) : (
                        filteredReplies.map(reply => {
                          const ensureUTC = (dateStr?: string) => dateStr ? (dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`) : undefined;
                          const replyTime = new Date(ensureUTC(reply.created_at) || reply.created_at);
                          const status = reply.review_status || "pending";
                          const isSelected = selectedReplyIds.includes(reply._id);
                          const isExpanded = expandedReplyId === reply._id;
                          return (
                            <div key={reply._id} className={`p-3 bg-card rounded-lg border shadow-sm transition-colors ${isSelected ? 'border-indigo-500 bg-indigo-50/10 dark:bg-indigo-950/20' : 'hover:border-indigo-300'}`}>
                              <div className="flex items-start gap-2">
                                <Checkbox className="mt-0.5" checked={isSelected} onCheckedChange={() => handleToggleSelect(reply._id)} />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center justify-between mb-1">
                                    <div className="flex items-center gap-1.5 min-w-0">
                                      <span className="text-xs font-bold truncate" title={reply.pseudonym}>{reply.pseudonym?.length > 12 ? `${reply.pseudonym.substring(0, 8)}...` : reply.pseudonym}</span>
                                      {reply.student_id && <span className="text-[11px] text-muted-foreground">({reply.student_id})</span>}
                                      {status === 'approved' && <span className="text-[10px] flex items-center bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-1 py-0.5 rounded"><CheckCircle2 className="w-2.5 h-2.5 mr-0.5"/>通過</span>}
                                      {status === 'rejected' && <span className="text-[10px] flex items-center bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 px-1 py-0.5 rounded"><XCircle className="w-2.5 h-2.5 mr-0.5"/>退回</span>}
                                      {status === 'pending' && <span className="text-[10px] bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 px-1 py-0.5 rounded">待批閱</span>}
                                    </div>
                                    <span className="text-[10px] text-muted-foreground whitespace-nowrap ml-2">{replyTime.toLocaleTimeString('zh-TW', {hour: '2-digit', minute:'2-digit'})}</span>
                                  </div>
                                  <p className={`text-sm text-foreground/90 cursor-pointer ${isExpanded ? 'whitespace-pre-wrap' : 'line-clamp-2'}`} onClick={() => setExpandedReplyId(isExpanded ? null : reply._id)}>{reply.question_text}</p>
                                  {reply.feedback && (
                                    <div className="mt-1.5 p-1.5 bg-indigo-50/50 dark:bg-indigo-900/10 rounded border border-indigo-100 dark:border-indigo-900/50">
                                      <p className="text-[11px] text-indigo-700 dark:text-indigo-400"><span className="font-semibold">評語：</span>{reply.feedback}</p>
                                    </div>
                                  )}
                                  <div className="flex justify-end mt-1.5">
                                    <Button variant="secondary" size="sm" className="h-6 text-[11px]" onClick={() => handleOpenReviewDialog(reply)}>{status === 'pending' ? '批閱' : '修改批閱'}</Button>
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center border rounded-lg bg-secondary/20">
                    <div className="text-center">
                      <MessageCircle className="w-10 h-10 mx-auto text-muted-foreground mb-2 opacity-40" />
                      <p className="text-sm text-muted-foreground">此任務未開放 LINE 互動作答</p>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center border rounded-lg border-dashed bg-secondary/20">
                <div className="text-center">
                  <Target className="w-12 h-12 mx-auto text-muted-foreground mb-3 opacity-40" />
                  <p className="text-muted-foreground">選擇左側任務查看詳細的診斷設定</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 新增 Q&A 對話框 */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center text-indigo-700 dark:text-indigo-400">
              <Target className="w-5 h-5 mr-2" /> 發布教育診斷任務
            </DialogTitle>
            <DialogDescription>設定您想探測的核心觀念與預期迷思，AI 將為您進行深度歸納分析。</DialogDescription>
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
              <Label htmlFor="question">老師的提問 <span className="text-destructive">*</span></Label>
              <Textarea id="question" placeholder="輸入要讓學生回答的探究問題..." value={newQA.question} onChange={(e) => setNewQA({ ...newQA, question: e.target.value })} rows={2} />
            </div>

            <div className="space-y-2 bg-indigo-50/50 dark:bg-indigo-950/20 p-3 rounded-lg border border-indigo-100 dark:border-indigo-900">
              <Label htmlFor="core_concept" className="text-indigo-700 dark:text-indigo-400 flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-1"/> 期望的核心觀念 <span className="text-destructive ml-1">*</span>
              </Label>
              <Textarea id="core_concept" placeholder="輸入您期望學生回答出的核心概念或正確推論邏輯，AI 會以此作為診斷的完美標準..." value={newQA.core_concept} onChange={(e) => setNewQA({ ...newQA, core_concept: e.target.value })} rows={3} className="bg-background"/>
            </div>

            <div className="space-y-2 bg-orange-50/50 dark:bg-orange-950/20 p-3 rounded-lg border border-orange-100 dark:border-orange-900">
              <Label htmlFor="expected_misconceptions" className="text-orange-700 dark:text-orange-400 flex items-center">
                <AlertTriangle className="w-4 h-4 mr-1"/> 探測迷思 / 分析重點 (選填)
              </Label>
              <Textarea id="expected_misconceptions" placeholder="例如：學生可能會混淆因果關係、可能會遺漏成本考量... (告訴 AI 幫您特別留意哪些常犯錯誤)" value={newQA.expected_misconceptions} onChange={(e) => setNewQA({ ...newQA, expected_misconceptions: e.target.value })} rows={2} className="bg-background"/>
            </div>

            <div className="p-4 border border-border rounded-lg space-y-4">
               <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="font-bold flex items-center">
                      <MessageCircle className="w-4 h-4 mr-2" /> 允許學生透過 LINE 即時作答
                    </Label>
                  </div>
                  <Switch checked={newQA.allow_replies} onCheckedChange={(checked) => setNewQA({ ...newQA, allow_replies: checked })} />
               </div>
               
               {newQA.allow_replies && (
                  <div className="pt-4 border-t border-border">
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
                           <span className="text-sm text-muted-foreground">分鐘後自動關閉通道</span>
                        </div>
                    ) : (
                        <div className="p-2 mb-4 bg-secondary/50 rounded border border-dashed border-border">
                           <p className="text-xs text-center text-muted-foreground">
                             ✨ 目前為<b>不限時模式</b>：學生可隨時作答，直到您手動點擊「立即結束任務」。
                           </p>
                        </div>
                    )}
                    
                    <div className="flex items-center justify-between pt-4 border-t border-border/50">
                       <Label className="block">每位學生作答次數上限</Label>
                       <div className="flex items-center gap-2">
                         <Input 
                           type="number" 
                           min="0" 
                           value={newQA.max_attempts} 
                           onChange={(e) => setNewQA({ ...newQA, max_attempts: Number(e.target.value) })}
                           className="w-24"
                         />
                         <span className="text-sm text-muted-foreground">次 (0為不限)</span>
                       </div>
                    </div>
                  </div>
               )}
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg mt-4">
              <div className="space-y-0.5">
                <Label htmlFor="publish">立即發布廣播</Label>
                <p className="text-sm text-muted-foreground">發布後將透過 LINE 通知所有學生</p>
              </div>
              <Switch id="publish" checked={newQA.is_published} onCheckedChange={(checked) => setNewQA({ ...newQA, is_published: checked })} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)} disabled={isCreating}>取消</Button>
            <Button onClick={handleCreateQA} disabled={isCreating} className="bg-indigo-600 hover:bg-indigo-700 text-white">
              {isCreating ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />發布中...</> : "發布診斷任務"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 編輯 Q&A 對話框 */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>編輯診斷任務</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>老師的提問 <span className="text-destructive">*</span></Label>
              <Textarea value={editQA.question} onChange={(e) => setEditQA({ ...editQA, question: e.target.value })} rows={2} />
            </div>
            
            <div className="space-y-2 bg-indigo-50/50 dark:bg-indigo-950/20 p-3 rounded-lg border border-indigo-100 dark:border-indigo-900">
              <Label className="text-indigo-700 dark:text-indigo-400">期望的核心觀念 <span className="text-destructive">*</span></Label>
              <Textarea value={editQA.core_concept} onChange={(e) => setEditQA({ ...editQA, core_concept: e.target.value })} rows={3} className="bg-background"/>
            </div>
            
            <div className="space-y-2 bg-orange-50/50 dark:bg-orange-950/20 p-3 rounded-lg border border-orange-100 dark:border-orange-900">
              <Label className="text-orange-700 dark:text-orange-400">探測迷思 / 分析重點</Label>
              <Textarea value={editQA.expected_misconceptions} onChange={(e) => setEditQA({ ...editQA, expected_misconceptions: e.target.value })} rows={2} className="bg-background"/>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg mt-4 bg-secondary/10">
               <Label>每位學生作答次數上限</Label>
               <div className="flex items-center gap-2">
                 <Input 
                   type="number" 
                   min="0" 
                   value={editQA.max_attempts} 
                   onChange={(e) => setEditQA({ ...editQA, max_attempts: Number(e.target.value) })}
                   className="w-24 bg-background"
                 />
                 <span className="text-sm text-muted-foreground">次 (0為不限)</span>
               </div>
            </div>
            
            <div className="flex items-center justify-between p-4 border rounded-lg mt-4">
              <div className="space-y-0.5">
                <Label>發布狀態</Label>
              </div>
              <Switch checked={editQA.is_published} onCheckedChange={(checked) => setEditQA({ ...editQA, is_published: checked })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>取消</Button>
            <Button onClick={handleEditQA} className="bg-indigo-600 hover:bg-indigo-700 text-white">{isEditing ? "更新中..." : "儲存設定"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 刪除確認對話框 */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle className="text-destructive">確認刪除</DialogTitle></DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteQA}>確認刪除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 單筆批閱對話框 */}
      <Dialog open={isReviewDialogOpen} onOpenChange={setIsReviewDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>人工審核學生作答</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="p-3 bg-secondary/50 rounded-lg text-sm border break-words">
              {/* =========== 🔥 修正：彈出視窗內的代號縮短 =========== */}
              <span className="font-bold block mb-1 text-xs text-muted-foreground break-all">
                學生 <span title={reviewingReply?.pseudonym}>{reviewingReply?.pseudonym?.length > 12 ? `${reviewingReply.pseudonym.substring(0, 8)}...` : reviewingReply?.pseudonym}</span> {reviewingReply?.student_id && `(${reviewingReply?.student_id})`} 的回答：
              </span>
              {/* =================================================== */}
              <div className="whitespace-pre-wrap">{reviewingReply?.question_text}</div>
            </div>
            
            <div className="space-y-3">
              <Label>審核此回答是否值得送交 AI 分析</Label>
              <div className="flex gap-2">
                <Button 
                  variant={reviewStatus === 'approved' ? 'default' : 'outline'} 
                  className={reviewStatus === 'approved' ? 'bg-green-600 hover:bg-green-700 text-white' : ''}
                  onClick={() => setReviewStatus('approved')}
                >
                  <CheckCircle2 className="w-4 h-4 mr-2"/> 通過 (有效作答)
                </Button>
                <Button 
                  variant={reviewStatus === 'rejected' ? 'default' : 'outline'}
                  className={reviewStatus === 'rejected' ? 'bg-red-600 hover:bg-red-700 text-white' : ''} 
                  onClick={() => setReviewStatus('rejected')}
                >
                  <XCircle className="w-4 h-4 mr-2"/> 退回 (無效/垃圾訊息)
                </Button>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <Label>給予學生私下評語 (選填)</Label>
              <Textarea 
                placeholder="寫下給學生的提示或鼓勵..." 
                value={reviewFeedback}
                onChange={(e) => setReviewFeedback(e.target.value)}
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsReviewDialogOpen(false)} disabled={isSubmittingReview}>取消</Button>
            <Button onClick={handleSubmitReview} disabled={isSubmittingReview} className="bg-indigo-600 hover:bg-indigo-700 text-white">
              {isSubmittingReview ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />儲存中...</> : "儲存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      <Dialog open={isReclusterDialogOpen} onOpenChange={setIsReclusterDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-orange-600 dark:text-orange-500 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              確認重新 AI 診斷？
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="mb-2 font-medium">這項操作將會進行「智慧重新批閱」：</p>
            <ul className="list-disc list-inside mt-2 space-y-1 text-muted-foreground text-sm">
              <li><strong>保留設定</strong>：您在「AI 聚類」頁面手動新增或鎖定的分類標籤將被保留。</li>
              <li><strong>清除舊檔</strong>：未鎖定的 AI 自動分類將會被清空刪除。</li>
              <li><strong>重新洗牌</strong>：AI 將重新審視所有已通過的學生回答，並<span className="text-indigo-600 dark:text-indigo-400 font-bold">優先將其分配至保留的分類中</span>。</li>
            </ul>
            <p className="mt-6 text-sm font-bold text-foreground">確定要繼續嗎？</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsReclusterDialogOpen(false)}>取消</Button>
            <Button className="bg-orange-600 hover:bg-orange-700 text-white" onClick={handleRunReclustering}>
              確認重新診斷
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}