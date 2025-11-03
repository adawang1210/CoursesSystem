"use client";
import { useState, useEffect } from "react";
import { Plus, Edit2, Trash2, Calendar, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  announcementsApi,
  coursesApi,
  type Announcement as ApiAnnouncement,
} from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface Announcement {
  id: string;
  title: string;
  content: string;
  author: string;
  course: string;
  courseId: string;
  publishedDate: string;
  isPublished: boolean;
}

export default function AnnouncementsPage() {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
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
      await loadAnnouncements();
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

  const loadAnnouncements = async () => {
    try {
      const response = await announcementsApi.getAll();
      const mappedAnnouncements: Announcement[] = response.map(
        (ann: ApiAnnouncement) => {
          const course = courses.find((c) => c._id === ann.course_id);
          return {
            id: ann._id || "",
            title: ann.title,
            content: ann.content,
            author: ann.created_by || "系統",
            course: course?.course_name || "未知課程",
            courseId: ann.course_id,
            publishedDate: ann.created_at
              ? new Date(ann.created_at).toISOString().split("T")[0]
              : "",
            isPublished: ann.is_published || false,
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
      !newAnnouncement.title ||
      !newAnnouncement.content ||
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
      await announcementsApi.create({
        course_id: newAnnouncement.courseId,
        title: newAnnouncement.title,
        content: newAnnouncement.content,
        is_published: true,
      });

      toast({
        title: "成功",
        description: "公告已發布",
      });

      setNewAnnouncement({
        title: "",
        content: "",
        courseId: courses[0]?._id || "",
      });
      setShowAddForm(false);
      await loadData();
    } catch (error) {
      console.error("發布公告失敗:", error);
      toast({
        title: "錯誤",
        description: "發布公告失敗",
        variant: "destructive",
      });
    }
  };

  const handleDeleteAnnouncement = async (id: string) => {
    try {
      await announcementsApi.delete(id);
      toast({
        title: "成功",
        description: "公告已刪除",
      });
      // 立即從本地狀態移除
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
          <p className="text-muted-foreground">發布和管理課程公告</p>
        </div>
        <Button onClick={() => setShowAddForm(!showAddForm)} className="gap-2">
          <Plus className="w-4 h-4" />
          發布公告
        </Button>
      </div>

      {showAddForm && (
        <Card className="bg-secondary/50 border-primary/20 mb-6">
          <CardContent className="pt-6 space-y-4">
            <Input
              placeholder="公告標題"
              value={newAnnouncement.title}
              onChange={(e) =>
                setNewAnnouncement({
                  ...newAnnouncement,
                  title: e.target.value,
                })
              }
            />
            <Textarea
              placeholder="公告內容"
              value={newAnnouncement.content}
              onChange={(e) =>
                setNewAnnouncement({
                  ...newAnnouncement,
                  content: e.target.value,
                })
              }
              className="min-h-24"
            />
            <select
              value={newAnnouncement.courseId}
              onChange={(e) =>
                setNewAnnouncement({
                  ...newAnnouncement,
                  courseId: e.target.value,
                })
              }
              className="w-full px-3 py-2 border border-input bg-background rounded-md"
            >
              <option value="">選擇課程</option>
              {courses.map((course) => (
                <option key={course._id} value={course._id}>
                  {course.course_name}
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <Button onClick={handleAddAnnouncement} className="flex-1">
                發布
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowAddForm(false)}
                className="flex-1"
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
              className="hover:shadow-md transition-shadow"
            >
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <CardTitle className="text-lg">
                      {announcement.title}
                    </CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
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
                <div className="flex justify-between items-center text-xs text-muted-foreground">
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
