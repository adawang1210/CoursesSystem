"use client";
import { useState, useEffect } from "react";
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
  ThumbsUp,
  Eye,
  Plus,
  Loader2,
  X,
  Trash2,
} from "lucide-react";
import { qasApi, coursesApi, type QA as ApiQA, type Course } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/auth-context";

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

  // 新增 QA 對話框狀態
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newQA, setNewQA] = useState({
    course_id: "",
    question: "",
    answer: "",
    category: "",
    tags: [] as string[],
    is_published: false,
  });
  const [tagInput, setTagInput] = useState("");

  // 刪除 QA 對話框狀態
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [qaToDelete, setQaToDelete] = useState<QAItem | null>(null);

  // 編輯 QA 對話框狀態
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

  // 載入課程資料
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
        // 如果有課程，預設選擇第一個
        if (response.length > 0 && response[0]._id) {
          setNewQA((prev) => ({ ...prev, course_id: response[0]._id || "" }));
        }
      } catch (error) {
        console.error("載入課程失敗:", error);
      }
    };
    fetchCourses();
  }, []);

  // 載入 Q&A 資料
  useEffect(() => {
    const fetchQAs = async () => {
      try {
        setIsLoading(true);
        const qas = await qasApi.getAll();
        const transformedQAs: QAItem[] = qas.map((qa) => ({
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
            ? new Date(qa.updated_at).toLocaleDateString("zh-TW")
            : new Date(qa.created_at || "").toLocaleDateString("zh-TW"),
        }));
        setQaList(transformedQAs);
      } catch (error) {
        console.error("載入 Q&A 失敗:", error);
        toast({
          variant: "destructive",
          title: "載入失敗",
          description: "無法載入 Q&A 資料，請稍後再試",
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchQAs();
  }, [courses, toast]);

  const filteredQAs = qaList.filter(
    (item) =>
      item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 處理新增 QA
  const handleCreateQA = async () => {
    // 驗證必填欄位
    if (!newQA.course_id) {
      toast({
        variant: "destructive",
        title: "錯誤",
        description: "請選擇課程",
      });
      return;
    }

    // 驗證課程是否存在
    const courseExists = courseList.some(
      (course) => course._id === newQA.course_id
    );
    if (!courseExists) {
      toast({
        variant: "destructive",
        title: "錯誤",
        description: "所選課程不存在，請重新選擇",
      });
      // 重置課程選擇
      setNewQA({ ...newQA, course_id: courseList[0]?._id || "" });
      return;
    }

    if (!newQA.question.trim()) {
      toast({
        variant: "destructive",
        title: "錯誤",
        description: "請輸入問題",
      });
      return;
    }
    if (!newQA.answer.trim()) {
      toast({
        variant: "destructive",
        title: "錯誤",
        description: "請輸入答案",
      });
      return;
    }

    try {
      setIsCreating(true);
      await qasApi.create({
        course_id: newQA.course_id,
        question: newQA.question.trim(),
        answer: newQA.answer.trim(),
        category: newQA.category.trim() || undefined,
        tags: newQA.tags.length > 0 ? newQA.tags : undefined,
        is_published: newQA.is_published,
        created_by: user?.username || "admin",
      });

      toast({
        title: "成功",
        description: "Q&A 已新增",
      });

      // 重置表單
      setNewQA({
        course_id: courseList[0]?._id || "",
        question: "",
        answer: "",
        category: "",
        tags: [],
        is_published: false,
      });
      setTagInput("");
      setIsCreateDialogOpen(false);

      // 重新載入 Q&A 列表
      const qas = await qasApi.getAll();
      const transformedQAs: QAItem[] = qas.map((qa) => ({
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
          ? new Date(qa.updated_at).toLocaleDateString("zh-TW")
          : new Date(qa.created_at || "").toLocaleDateString("zh-TW"),
      }));
      setQaList(transformedQAs);
    } catch (error: any) {
      console.error("新增 Q&A 失敗:", error);

      // 檢查是否為課程不存在的錯誤
      let errorMessage = "無法新增 Q&A，請稍後再試";
      if (error?.response?.status === 400) {
        errorMessage =
          error?.response?.data?.detail || "課程不存在或資料有誤，請檢查後重試";
      }

      toast({
        variant: "destructive",
        title: "新增失敗",
        description: errorMessage,
      });
    } finally {
      setIsCreating(false);
    }
  };

  // 處理新增標籤
  const handleAddTag = () => {
    const trimmedTag = tagInput.trim();
    if (trimmedTag && !newQA.tags.includes(trimmedTag)) {
      setNewQA({ ...newQA, tags: [...newQA.tags, trimmedTag] });
      setTagInput("");
    }
  };

  // 處理移除標籤
  const handleRemoveTag = (tagToRemove: string) => {
    setNewQA({
      ...newQA,
      tags: newQA.tags.filter((tag) => tag !== tagToRemove),
    });
  };

  // 處理打開新增對話框
  const handleOpenCreateDialog = () => {
    // 檢查是否有可用的課程
    if (courseList.length === 0) {
      toast({
        variant: "destructive",
        title: "無法新增 Q&A",
        description: "目前沒有可用的課程，請先建立課程",
      });
      return;
    }

    // 重置表單
    setNewQA({
      course_id: courseList[0]?._id || "",
      question: "",
      answer: "",
      category: "",
      tags: [],
      is_published: false,
    });
    setTagInput("");
    setIsCreateDialogOpen(true);
  };

  // 處理打開編輯對話框
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

  // 處理編輯 QA
  const handleEditQA = async () => {
    // 驗證必填欄位
    if (!editQA.question.trim()) {
      toast({
        variant: "destructive",
        title: "錯誤",
        description: "請輸入問題",
      });
      return;
    }
    if (!editQA.answer.trim()) {
      toast({
        variant: "destructive",
        title: "錯誤",
        description: "請輸入答案",
      });
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

      toast({
        title: "成功",
        description: "Q&A 已更新",
      });

      // 關閉對話框
      setIsEditDialogOpen(false);

      // 重新載入 Q&A 列表
      const qas = await qasApi.getAll();
      const transformedQAs: QAItem[] = qas.map((qa) => ({
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
          ? new Date(qa.updated_at).toLocaleDateString("zh-TW")
          : new Date(qa.created_at || "").toLocaleDateString("zh-TW"),
      }));
      setQaList(transformedQAs);

      // 更新選中的 QA
      if (selectedQA?.id === editQA.id) {
        const updatedQA = transformedQAs.find((qa) => qa.id === editQA.id);
        if (updatedQA) {
          setSelectedQA(updatedQA);
        }
      }
    } catch (error) {
      console.error("更新 Q&A 失敗:", error);
      toast({
        variant: "destructive",
        title: "更新失敗",
        description: "無法更新 Q&A，請稍後再試",
      });
    } finally {
      setIsEditing(false);
    }
  };

  // 處理編輯時新增標籤
  const handleAddEditTag = () => {
    const trimmedTag = editTagInput.trim();
    if (trimmedTag && !editQA.tags.includes(trimmedTag)) {
      setEditQA({ ...editQA, tags: [...editQA.tags, trimmedTag] });
      setEditTagInput("");
    }
  };

  // 處理編輯時移除標籤
  const handleRemoveEditTag = (tagToRemove: string) => {
    setEditQA({
      ...editQA,
      tags: editQA.tags.filter((tag) => tag !== tagToRemove),
    });
  };

  // 處理打開刪除對話框
  const handleOpenDeleteDialog = (qa: QAItem) => {
    setQaToDelete(qa);
    setIsDeleteDialogOpen(true);
  };

  // 處理刪除 QA
  const handleDeleteQA = async () => {
    if (!qaToDelete) return;

    try {
      setIsDeleting(true);
      await qasApi.delete(qaToDelete.id);

      toast({
        title: "成功",
        description: "Q&A 已刪除",
      });

      // 關閉對話框
      setIsDeleteDialogOpen(false);
      setQaToDelete(null);

      // 如果刪除的是當前選中的 QA，清除選中狀態
      if (selectedQA?.id === qaToDelete.id) {
        setSelectedQA(null);
      }

      // 重新載入 Q&A 列表
      const qas = await qasApi.getAll();
      const transformedQAs: QAItem[] = qas.map((qa) => ({
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
          ? new Date(qa.updated_at).toLocaleDateString("zh-TW")
          : new Date(qa.created_at || "").toLocaleDateString("zh-TW"),
      }));
      setQaList(transformedQAs);
    } catch (error) {
      console.error("刪除 Q&A 失敗:", error);
      toast({
        variant: "destructive",
        title: "刪除失敗",
        description: "無法刪除 Q&A，請稍後再試",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-foreground mb-2">Q&A 管理</h1>
      <p className="text-muted-foreground mb-8">瀏覽和管理 Q&A 對</p>

      <div className="flex gap-4 items-center mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="搜尋問題..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button className="whitespace-nowrap" onClick={handleOpenCreateDialog}>
          <Plus className="w-4 h-4 mr-2" />
          新增 Q&A
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">載入中...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* QA List */}
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
                      建立第一個 Q&A
                    </Button>
                  )}
                </CardContent>
              </Card>
            ) : (
              filteredQAs.map((qa) => (
                <Card
                  key={qa.id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => setSelectedQA(qa)}
                >
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-semibold text-foreground flex-1">
                        {qa.question}
                      </h3>
                      {!qa.isPublished && (
                        <span className="text-xs bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 px-2 py-1 rounded ml-2">
                          草稿
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                      {qa.answer}
                    </p>
                    <div className="flex justify-between items-center text-xs">
                      <div className="flex gap-2 flex-wrap">
                        {qa.tags.slice(0, 3).map((tag, index) => (
                          <span
                            key={index}
                            className="bg-secondary text-secondary-foreground px-2 py-1 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                      <span className="bg-primary/10 text-primary px-2 py-1 rounded">
                        {qa.course}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>

          {/* QA Detail Panel */}
          <div className="lg:col-span-1">
            {selectedQA ? (
              <Card className="sticky top-8">
                <CardHeader>
                  <CardTitle className="text-lg">詳細信息</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-xs uppercase text-muted-foreground mb-1">
                      問題
                    </p>
                    <p className="font-medium">{selectedQA.question}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase text-muted-foreground mb-1">
                      答案
                    </p>
                    <p className="text-sm">{selectedQA.answer}</p>
                  </div>
                  {selectedQA.category && (
                    <div>
                      <p className="text-xs uppercase text-muted-foreground mb-1">
                        分類
                      </p>
                      <p className="text-sm">{selectedQA.category}</p>
                    </div>
                  )}
                  {selectedQA.tags.length > 0 && (
                    <div>
                      <p className="text-xs uppercase text-muted-foreground mb-1">
                        標籤
                      </p>
                      <div className="flex gap-2 flex-wrap">
                        {selectedQA.tags.map((tag, index) => (
                          <span
                            key={index}
                            className="text-xs bg-secondary text-secondary-foreground px-2 py-1 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-2 pt-4 border-t">
                    <div>
                      <p className="text-xs text-muted-foreground">作者</p>
                      <p className="font-medium text-sm">{selectedQA.author}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">更新時間</p>
                      <p className="font-medium text-sm">
                        {selectedQA.lastUpdated}
                      </p>
                    </div>
                  </div>
                  <div className="pt-2">
                    <p className="text-xs text-muted-foreground mb-1">狀態</p>
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        selectedQA.isPublished
                          ? "bg-green-500/10 text-green-600 dark:text-green-400"
                          : "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
                      }`}
                    >
                      {selectedQA.isPublished ? "已發布" : "草稿"}
                    </span>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Button
                      className="flex-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenEditDialog(selectedQA);
                      }}
                    >
                      編輯
                    </Button>
                    <Button
                      variant="destructive"
                      className="flex-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenDeleteDialog(selectedQA);
                      }}
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      刪除
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="bg-secondary/30 border-dashed flex items-center justify-center min-h-96">
                <CardContent className="text-center">
                  <MessageCircle className="w-12 h-12 mx-auto text-muted-foreground mb-3 opacity-50" />
                  <p className="text-muted-foreground">
                    選擇一個 Q&A 查看詳細信息
                  </p>
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
            <DialogTitle>新增 Q&A</DialogTitle>
            <DialogDescription>建立一個新的問答對</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* 課程選擇 */}
            <div className="space-y-2">
              <Label htmlFor="course">
                課程 <span className="text-destructive">*</span>
              </Label>
              <Select
                value={newQA.course_id}
                onValueChange={(value) =>
                  setNewQA({ ...newQA, course_id: value })
                }
              >
                <SelectTrigger id="course">
                  <SelectValue placeholder="選擇課程" />
                </SelectTrigger>
                <SelectContent>
                  {courseList.map((course) => (
                    <SelectItem key={course._id} value={course._id || ""}>
                      {course.course_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 問題 */}
            <div className="space-y-2">
              <Label htmlFor="question">
                問題 <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="question"
                placeholder="輸入問題..."
                value={newQA.question}
                onChange={(e) =>
                  setNewQA({ ...newQA, question: e.target.value })
                }
                rows={3}
              />
            </div>

            {/* 答案 */}
            <div className="space-y-2">
              <Label htmlFor="answer">
                答案 <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="answer"
                placeholder="輸入答案..."
                value={newQA.answer}
                onChange={(e) => setNewQA({ ...newQA, answer: e.target.value })}
                rows={5}
              />
            </div>

            {/* 分類 */}
            <div className="space-y-2">
              <Label htmlFor="category">分類（選填）</Label>
              <Input
                id="category"
                placeholder="例如：程式設計、數學、物理"
                value={newQA.category}
                onChange={(e) =>
                  setNewQA({ ...newQA, category: e.target.value })
                }
              />
            </div>

            {/* 標籤 */}
            <div className="space-y-2">
              <Label htmlFor="tags">標籤（選填）</Label>
              <div className="flex gap-2">
                <Input
                  id="tags"
                  placeholder="輸入標籤後按 Enter 或點擊新增"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddTag();
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleAddTag}
                  disabled={!tagInput.trim()}
                >
                  新增
                </Button>
              </div>
              {newQA.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {newQA.tags.map((tag, index) => (
                    <div
                      key={index}
                      className="bg-secondary text-secondary-foreground px-3 py-1 rounded-md flex items-center gap-2"
                    >
                      <span>{tag}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(tag)}
                        className="hover:text-destructive"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 發布狀態 */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-0.5">
                <Label htmlFor="publish">立即發布</Label>
                <p className="text-sm text-muted-foreground">
                  發布後學生即可看到此 Q&A
                </p>
              </div>
              <Switch
                id="publish"
                checked={newQA.is_published}
                onCheckedChange={(checked) =>
                  setNewQA({ ...newQA, is_published: checked })
                }
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsCreateDialogOpen(false)}
              disabled={isCreating}
            >
              取消
            </Button>
            <Button onClick={handleCreateQA} disabled={isCreating}>
              {isCreating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  建立中...
                </>
              ) : (
                "建立 Q&A"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 編輯 Q&A 對話框 */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>編輯 Q&A</DialogTitle>
            <DialogDescription>修改問答對的內容</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* 課程顯示（不可編輯） */}
            <div className="space-y-2">
              <Label>課程</Label>
              <div className="p-2 bg-secondary/50 rounded-md text-sm">
                {courses.get(editQA.course_id) || editQA.course_id}
              </div>
              <p className="text-xs text-muted-foreground">課程資訊無法修改</p>
            </div>

            {/* 問題 */}
            <div className="space-y-2">
              <Label htmlFor="edit-question">
                問題 <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="edit-question"
                placeholder="輸入問題..."
                value={editQA.question}
                onChange={(e) =>
                  setEditQA({ ...editQA, question: e.target.value })
                }
                rows={3}
              />
            </div>

            {/* 答案 */}
            <div className="space-y-2">
              <Label htmlFor="edit-answer">
                答案 <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="edit-answer"
                placeholder="輸入答案..."
                value={editQA.answer}
                onChange={(e) =>
                  setEditQA({ ...editQA, answer: e.target.value })
                }
                rows={5}
              />
            </div>

            {/* 分類 */}
            <div className="space-y-2">
              <Label htmlFor="edit-category">分類（選填）</Label>
              <Input
                id="edit-category"
                placeholder="例如：程式設計、數學、物理"
                value={editQA.category}
                onChange={(e) =>
                  setEditQA({ ...editQA, category: e.target.value })
                }
              />
            </div>

            {/* 標籤 */}
            <div className="space-y-2">
              <Label htmlFor="edit-tags">標籤（選填）</Label>
              <div className="flex gap-2">
                <Input
                  id="edit-tags"
                  placeholder="輸入標籤後按 Enter 或點擊新增"
                  value={editTagInput}
                  onChange={(e) => setEditTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddEditTag();
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleAddEditTag}
                  disabled={!editTagInput.trim()}
                >
                  新增
                </Button>
              </div>
              {editQA.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {editQA.tags.map((tag, index) => (
                    <div
                      key={index}
                      className="bg-secondary text-secondary-foreground px-3 py-1 rounded-md flex items-center gap-2"
                    >
                      <span>{tag}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveEditTag(tag)}
                        className="hover:text-destructive"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 發布狀態 */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-0.5">
                <Label htmlFor="edit-publish">發布狀態</Label>
                <p className="text-sm text-muted-foreground">
                  發布後學生即可看到此 Q&A
                </p>
              </div>
              <Switch
                id="edit-publish"
                checked={editQA.is_published}
                onCheckedChange={(checked) =>
                  setEditQA({ ...editQA, is_published: checked })
                }
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsEditDialogOpen(false)}
              disabled={isEditing}
            >
              取消
            </Button>
            <Button onClick={handleEditQA} disabled={isEditing}>
              {isEditing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  更新中...
                </>
              ) : (
                "儲存變更"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 刪除確認對話框 */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>確認刪除</DialogTitle>
            <DialogDescription>
              您確定要刪除這個 Q&A 嗎？此操作無法復原。
            </DialogDescription>
          </DialogHeader>

          {qaToDelete && (
            <div className="py-4">
              <div className="space-y-2 p-4 bg-secondary/50 rounded-lg">
                <div>
                  <p className="text-sm font-semibold text-muted-foreground">
                    問題：
                  </p>
                  <p className="text-sm">{qaToDelete.question}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-muted-foreground">
                    答案：
                  </p>
                  <p className="text-sm line-clamp-3">{qaToDelete.answer}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-muted-foreground">
                    課程：
                  </p>
                  <p className="text-sm">{qaToDelete.course}</p>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsDeleteDialogOpen(false)}
              disabled={isDeleting}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteQA}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  刪除中...
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-2" />
                  確認刪除
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
