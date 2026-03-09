"use client";
import { useState, useEffect } from "react";
import { 
  Plus, Edit2, Trash2, Calendar, User, 
  Send, Loader2, MessageSquareWarning 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  announcementsApi,
  coursesApi,
  type Announcement as ApiAnnouncement,
} from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/auth-context";

interface Announcement {
  id: string;
  title: string;
  content: string;
  author: string;
  course: string;
  courseId: string;
  publishedDate: string;
  isPublished: boolean;
  sentToLine: boolean; // 🔥 新增：記錄是否已推播至 LINE
}

export default function AnnouncementsPage() {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false); // 🔥 新增：發布中的載入狀態
  
  const { user } = useAuth(); // 取得當前登入的老師資訊
  
  const [newAnnouncement, setNewAnnouncement] = useState({
    title: "",
    content: "",
    courseId: "",
  });
  const { toast } = useToast();

  // 載入課程和公告資料
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      // 載入課程
      const loadedCourses = await coursesApi.getAll();
      setCourses(loadedCourses);

      // 預設選擇第一個課程
      if (loadedCourses.length > 0 && !newAnnouncement.courseId) {
        setNewAnnouncement((prev) => ({
          ...prev,
          courseId: loadedCourses[0]._id || "",
        }));
      }

      // 載入公告
      await loadAnnouncements(loadedCourses);
    } catch (error) {
      console.error("載入資料失敗:", error);
      toast({
        title: "錯誤",
        description: "載入資料失敗",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadAnnouncements = async (currentCourses: any[] = courses) => {
    try {
      const response = await announcementsApi.getAll();
      const mappedAnnouncements: Announcement[] = response.map(
        (ann: any) => {
          const course = currentCourses.find((c) => c._id === ann.course_id);
          return {
            id: ann._id || "",
            title: ann.title,
            content: ann.content,
            author: ann.created_by || "系統",
            course: course?.course_name || "未知課程",
            courseId: ann.course_id,
            publishedDate: ann.created_at
              ? new Date(ann.created_at).toLocaleDateString("zh-TW")
              : "",
            isPublished: ann.is_published || false,
            sentToLine: ann.sent_to_line || false, // 🔥 讀取後端的推播狀態
          };
        }
      );
      setAnnouncements(mappedAnnouncements);
    } catch (error) {
      console.error("載入公告失敗:", error);
    }
  };

  const handleAddAnnouncement = async () => {
    if (
      !newAnnouncement.title.trim() ||
      !newAnnouncement.content.trim() ||
      !newAnnouncement.courseId
    ) {
      toast({
        title: "錯誤",
        description: "請填寫所有欄位",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsPublishing(true);
      // 🔥 呼叫 API，後端接收到 is_published: true 就會自動觸發 LINE 推播！
      await announcementsApi.create({
        course_id: newAnnouncement.courseId,
        title: newAnnouncement.title.trim(),
        content: newAnnouncement.content.trim(),
        is_published: true, 
      });

      toast({
        title: "成功",
        description: "公告已發布並推播至 LINE 群組！",
      });

      setNewAnnouncement({
        title: "",
        content: "",
        courseId: courses[0]?._id || "",
      });
      setShowAddForm(false);
      await loadAnnouncements();
    } catch (error) {
      console.error("發布公告失敗:", error);
      toast({
        title: "錯誤",
        description: "發布公告失敗",
        variant: "destructive",
      });
    } finally {
      setIsPublishing(false);
    }
  };

  const handleDeleteAnnouncement = async (id: string) => {
    try {
      await announcementsApi.delete(id);
      toast({
        title: "成功",
        description: "公告已刪除",
      });
      setAnnouncements(announcements.filter((ann) => ann.id !== id));
    } catch (error) {
      console.error("刪除公告失敗:", error);
      toast({
        title: "錯誤",
        description: "刪除公告失敗",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold text-foreground mb-2">公告管理</h1>
          <p className="text-muted-foreground">發布並自動推播課程公告給學生</p>
        </div>
        <Button onClick={() => setShowAddForm(!showAddForm)} className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white">
          <Plus className="w-4 h-4" />
          發布新公告
        </Button>
      </div>

      {showAddForm && (
        <Card className="bg-secondary/50 border-primary/20 mb-6 shadow-md border-indigo-200 dark:border-indigo-900">
          <CardHeader>
            <CardTitle className="text-lg">新增推播公告</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
             <div className="space-y-2">
              <Label>課程</Label>
              {/* 🔥 升級為更美觀的 Select 元件 */}
              <Select 
                value={newAnnouncement.courseId} 
                onValueChange={(value) => setNewAnnouncement({...newAnnouncement, courseId: value})}
              >
                <SelectTrigger className="bg-background">
                  <SelectValue placeholder="選擇要推播的課程" />
                </SelectTrigger>
                <SelectContent>
                  {courses.map((course) => (
                    <SelectItem key={course._id} value={course._id}>{course.course_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>公告標題</Label>
              <Input
                placeholder="例如：期中考範圍異動通知"
                value={newAnnouncement.title}
                onChange={(e) =>
                  setNewAnnouncement({
                    ...newAnnouncement,
                    title: e.target.value,
                  })
                }
                className="bg-background"
              />
            </div>
            
            <div className="space-y-2">
              <Label>公告內容</Label>
              <Textarea
                placeholder="輸入要廣播給學生的詳細內容..."
                value={newAnnouncement.content}
                onChange={(e) =>
                  setNewAnnouncement({
                    ...newAnnouncement,
                    content: e.target.value,
                  })
                }
                className="min-h-32 bg-background"
              />
            </div>

            {/* 🔥 新增推播提示區塊 */}
            <div className="flex items-start p-4 border rounded-lg mt-4 bg-indigo-50/50 dark:bg-indigo-950/20 border-indigo-100 dark:border-indigo-900">
               <MessageSquareWarning className="w-5 h-5 text-indigo-600 mt-0.5 mr-3 flex-shrink-0" />
               <div className="space-y-1">
                 <Label className="text-indigo-700 dark:text-indigo-400 font-bold">
                   立即推播至 LINE
                 </Label>
                 <p className="text-sm text-muted-foreground">
                   點擊下方「確認發布」後，系統將會立刻把此公告廣播給綁定該課程的所有學生。
                 </p>
               </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button 
                onClick={handleAddAnnouncement} 
                className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white"
                disabled={isPublishing}
              >
                {isPublishing ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin"/> 廣播中...</>
                ) : (
                  <><Send className="w-4 h-4 mr-2"/> 確認發布並推播</>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowAddForm(false)}
                className="flex-1"
                disabled={isPublishing}
              >
                取消
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <Card className="bg-secondary/30">
          <CardContent className="pt-12 pb-12 text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary mb-4" />
            <p className="text-muted-foreground">載入中...</p>
          </CardContent>
        </Card>
      ) : announcements.length === 0 ? (
        <Card className="bg-secondary/30 border-dashed">
          <CardContent className="pt-12 pb-12 text-center">
            <p className="text-muted-foreground">尚無公告</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {announcements.map((announcement) => (
            <Card
              key={announcement.id}
              className="hover:shadow-md transition-shadow border-l-4 border-l-transparent hover:border-l-indigo-600"
            >
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-3">
                      {announcement.title}
                      {/* 🔥 新增已推播至 LINE 的徽章 */}
                      {announcement.sentToLine && (
                        <span className="flex items-center text-xs font-normal bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-1 rounded-full">
                          <Send className="w-3 h-3 mr-1" /> 已推播至 LINE
                        </span>
                      )}
                    </CardTitle>
                    <p className="text-sm text-muted-foreground mt-2 whitespace-pre-wrap">
                      {announcement.content}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button className="p-1 hover:bg-secondary rounded">
                      <Edit2 className="w-4 h-4 text-muted-foreground" />
                    </button>
                    <button
                      onClick={() => handleDeleteAnnouncement(announcement.id)}
                      className="p-1 hover:bg-destructive/10 rounded"
                    >
                      <Trash2 className="w-4 h-4 text-destructive" />
                    </button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between items-center text-xs text-muted-foreground pt-3 border-t">
                  <div className="flex gap-4">
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3" />
                      {announcement.author}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {announcement.publishedDate}
                    </span>
                  </div>
                  <span className="bg-primary/10 text-primary px-2 py-1 rounded">
                    {announcement.course}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}