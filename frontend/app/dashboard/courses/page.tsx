"use client";
import { useState, useEffect } from "react";
import {
  Plus,
  Edit2,
  Trash2,
  Users,
  Calendar,
  ClipboardList,
  BookOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { coursesApi, type Course as ApiCourse } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface Course {
  id: string;
  name: string;
  code: string;
  semester: string;
  students: number;
  questions: number;
  createdDate: string;
}

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAddCourse, setShowAddCourse] = useState(false);
  const [newCourse, setNewCourse] = useState({
    name: "",
    code: "",
    semester: "",
  });
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  // 載入課程資料
  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    try {
      setLoading(true);
      const courses = await coursesApi.getAll({ is_active: true });
      const mappedCourses: Course[] = courses.map((c: any) => ({
        id: c._id || "",
        name: c.course_name,
        code: c.course_code,
        semester: c.semester,
        students: c.student_count || 0, // 從後端獲取實際學生數
        questions: c.question_count || 0, // 從後端獲取實際提問數
        createdDate: c.created_at
          ? new Date(c.created_at).toISOString().split("T")[0]
          : "",
      }));
      setCourses(mappedCourses);
    } catch (error) {
      console.error("載入課程失敗:", error);
      toast({
        title: "錯誤",
        description: "載入課程資料失敗，請確認後端服務是否正常運行",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const filteredCourses = courses.filter(
    (course) =>
      course.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      course.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddCourse = async () => {
    if (newCourse.name && newCourse.code && newCourse.semester) {
      try {
        const response = await coursesApi.create({
          course_name: newCourse.name,
          course_code: newCourse.code,
          semester: newCourse.semester,
          is_active: true,
        });

        if (response) {
          toast({
            title: "成功",
            description: "課程已成功創建",
          });
          setNewCourse({ name: "", code: "", semester: "" });
          setShowAddCourse(false);
          loadCourses(); // 重新載入課程列表
        }
      } catch (error) {
        console.error("創建課程失敗:", error);
        toast({
          title: "錯誤",
          description: "創建課程失敗，請稍後再試",
          variant: "destructive",
        });
      }
    }
  };

  const handleEditCourse = (course: Course) => {
    setEditingCourse(course);
    setShowAddCourse(false);
  };

  const handleUpdateCourse = async () => {
    if (editingCourse && editingCourse.id) {
      try {
        await coursesApi.update(editingCourse.id, {
          course_name: editingCourse.name,
          semester: editingCourse.semester,
        });
        toast({
          title: "成功",
          description: "課程已成功更新",
        });
        setEditingCourse(null);
        loadCourses(); // 重新載入課程列表
      } catch (error) {
        console.error("更新課程失敗:", error);
        toast({
          title: "錯誤",
          description: "更新課程失敗，請稍後再試",
          variant: "destructive",
        });
      }
    }
  };

  const handleDeleteCourse = async (id: string) => {
    try {
      await coursesApi.delete(id);
      toast({
        title: "成功",
        description: "課程已成功刪除",
      });
      setCourses(courses.filter((course) => course.id !== id));
    } catch (error) {
      console.error("刪除課程失敗:", error);
      toast({
        title: "錯誤",
        description: "刪除課程失敗，請稍後再試",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">課程管理</h1>
        <p className="text-muted-foreground">添加、編輯和管理你的教學課程</p>
      </div>
      <div className="flex justify-between items-center mb-6">
        <Button
          onClick={() => setShowAddCourse(!showAddCourse)}
          className="gap-2"
        >
          <Plus className="w-4 h-4" />
          新增課程
        </Button>
      </div>

      {showAddCourse && (
        <Card className="bg-secondary/50 border-primary/20 mb-6">
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Input
                placeholder="課程名稱"
                value={newCourse.name}
                onChange={(e) =>
                  setNewCourse({ ...newCourse, name: e.target.value })
                }
              />
              <Input
                placeholder="課程代碼"
                value={newCourse.code}
                onChange={(e) =>
                  setNewCourse({ ...newCourse, code: e.target.value })
                }
              />
              <Input
                placeholder="學期 (例如: 113-1)"
                value={newCourse.semester}
                onChange={(e) =>
                  setNewCourse({ ...newCourse, semester: e.target.value })
                }
              />
              <div className="flex gap-2">
                <Button onClick={handleAddCourse} className="flex-1">
                  新增
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowAddCourse(false)}
                  className="flex-1"
                >
                  取消
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {editingCourse && (
        <Card className="bg-secondary/50 border-primary/20 mb-6">
          <CardContent className="pt-6">
            <h3 className="text-lg font-semibold mb-4">編輯課程</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Input
                placeholder="課程名稱"
                value={editingCourse.name}
                onChange={(e) =>
                  setEditingCourse({ ...editingCourse, name: e.target.value })
                }
              />
              <Input
                placeholder="課程代碼"
                value={editingCourse.code}
                disabled
                className="bg-muted"
              />
              <Input
                placeholder="學期 (例如: 113-1)"
                value={editingCourse.semester}
                onChange={(e) =>
                  setEditingCourse({
                    ...editingCourse,
                    semester: e.target.value,
                  })
                }
              />
              <div className="flex gap-2">
                <Button onClick={handleUpdateCourse} className="flex-1">
                  更新
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setEditingCourse(null)}
                  className="flex-1"
                >
                  取消
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mb-6">
        <Input
          placeholder="搜尋課程名稱或課程代碼..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-md"
        />
      </div>

      {loading ? (
        <Card className="bg-secondary/30">
          <CardContent className="pt-12 pb-12 text-center">
            <p className="text-muted-foreground">載入中...</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredCourses.map((course) => (
              <Card
                key={course.id}
                className="hover:shadow-lg transition-shadow"
              >
                <CardHeader className="pb-3">
                  <div className="flex justify-between items-start gap-4">
                    <div>
                      <CardTitle className="text-lg">{course.name}</CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">
                        {course.code}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        學期: {course.semester}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditCourse(course)}
                        className="p-1 hover:bg-secondary rounded"
                      >
                        <Edit2 className="w-4 h-4 text-muted-foreground" />
                      </button>
                      <button
                        onClick={() => handleDeleteCourse(course.id)}
                        className="p-1 hover:bg-destructive/10 rounded"
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm">
                      <Users className="w-4 h-4 text-primary" />
                      <span>{course.students} 位學生</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <ClipboardList className="w-4 h-4 text-accent" />
                      <span>{course.questions} 個提問</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <Calendar className="w-4 h-4 text-muted-foreground" />
                      <span>{course.createdDate}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {filteredCourses.length === 0 && !loading && (
            <Card className="bg-secondary/30 border-dashed">
              <CardContent className="pt-12 pb-12 text-center">
                <BookOpen className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
                <p className="text-muted-foreground">沒有符合的課程</p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
