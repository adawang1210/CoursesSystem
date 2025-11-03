"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Users,
  MessageSquare,
  CheckCircle,
  Download,
  RefreshCw,
} from "lucide-react";
import {
  reportsApi,
  coursesApi,
  type Statistics,
  type ClusterSummary,
  type Course,
} from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export default function StatisticsPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>("");
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const { toast } = useToast();

  // 載入課程列表
  useEffect(() => {
    loadCourses();
  }, []);

  // 當課程選擇改變時，載入統計資料
  useEffect(() => {
    if (selectedCourse) {
      loadStatistics();
      loadClusters();
    }
  }, [selectedCourse]);

  const loadCourses = async () => {
    try {
      const courses = await coursesApi.getAll();
      if (courses.length > 0) {
        setCourses(courses);
        setSelectedCourse(courses[0]._id || "");
      }
    } catch (error) {
      console.error("載入課程失敗:", error);
      toast({
        title: "錯誤",
        description: "無法載入課程列表",
        variant: "destructive",
      });
    }
  };

  const loadStatistics = async () => {
    if (!selectedCourse) return;

    try {
      setLoading(true);
      const response = await reportsApi.getStatistics({
        course_id: selectedCourse,
      });
      if (response.success) {
        setStatistics(response.data);
      }
    } catch (error) {
      console.error("載入統計資料失敗:", error);
      toast({
        title: "錯誤",
        description: "無法載入統計資料",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadClusters = async () => {
    if (!selectedCourse) return;

    try {
      const response = await reportsApi.getClustersSummary(selectedCourse);
      if (response.success) {
        setClusters(response.data);
      }
    } catch (error) {
      console.error("載入聚類資料失敗:", error);
    }
  };

  const handleExport = async (type: "questions" | "qas" | "statistics") => {
    if (!selectedCourse) {
      toast({
        title: "提示",
        description: "請先選擇課程",
        variant: "destructive",
      });
      return;
    }

    try {
      setExporting(type);
      let blob: Blob;

      switch (type) {
        case "questions":
          blob = await reportsApi.exportQuestions({
            course_id: selectedCourse,
          });
          break;
        case "qas":
          blob = await reportsApi.exportQAs({ course_id: selectedCourse });
          break;
        case "statistics":
          blob = await reportsApi.exportStatistics({
            course_id: selectedCourse,
          });
          break;
      }

      // 下載檔案
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${type}_${selectedCourse}_${new Date().getTime()}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: "成功",
        description: "資料匯出成功",
      });
    } catch (error) {
      console.error("匯出失敗:", error);
      toast({
        title: "錯誤",
        description: "匯出資料失敗",
        variant: "destructive",
      });
    } finally {
      setExporting(null);
    }
  };

  // 準備圖表資料
  const statusChartData =
    statistics && statistics.status_distribution
      ? Object.entries(statistics.status_distribution).map(
          ([status, count]) => ({
            name: getStatusLabel(status),
            value: count,
            fill: getStatusColor(status),
          })
        )
      : [];

  const clusterChartData = clusters.slice(0, 10).map((cluster) => ({
    name: `群組 ${cluster.cluster_id}`,
    count: cluster.question_count,
    difficulty: cluster.avg_difficulty.toFixed(2),
  }));

  function getStatusLabel(status: string): string {
    const labels: { [key: string]: string } = {
      PENDING: "待處理",
      APPROVED: "已同意",
      REJECTED: "已拒絕",
      DELETED: "已刪除",
      WITHDRAWN: "已撤回",
    };
    return labels[status] || status;
  }

  function getStatusColor(status: string): string {
    const colors: { [key: string]: string } = {
      PENDING: "#fbbf24",
      APPROVED: "#10b981",
      REJECTED: "#ef4444",
      DELETED: "#6b7280",
      WITHDRAWN: "#8b5cf6",
    };
    return colors[status] || "#9ca3af";
  }

  const selectedCourseName =
    courses.find((c) => c._id === selectedCourse)?.course_name || "";

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">統計報表</h1>
        <p className="text-muted-foreground">查看平台統計數據和分析</p>
      </div>

      {/* 課程選擇器 */}
      <div className="mb-6 flex items-center gap-4">
        <div className="flex-1 max-w-md">
          <Select value={selectedCourse} onValueChange={setSelectedCourse}>
            <SelectTrigger>
              <SelectValue placeholder="選擇課程" />
            </SelectTrigger>
            <SelectContent>
              {courses.map((course) => (
                <SelectItem key={course._id} value={course._id || ""}>
                  {course.course_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline"
          size="icon"
          onClick={() => {
            loadStatistics();
            loadClusters();
          }}
          disabled={loading || !selectedCourse}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {!selectedCourse ? (
        <Card className="p-8">
          <div className="text-center text-muted-foreground">
            請選擇課程以查看統計資料
          </div>
        </Card>
      ) : loading ? (
        <Card className="p-8">
          <div className="text-center text-muted-foreground">載入中...</div>
        </Card>
      ) : !statistics ? (
        <Card className="p-8">
          <div className="text-center text-muted-foreground">
            無法載入統計資料
          </div>
        </Card>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <Card>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-muted-foreground">總提問數</p>
                    <p className="text-3xl font-bold text-primary">
                      {statistics.total_questions}
                    </p>
                  </div>
                  <MessageSquare className="w-8 h-8 text-primary opacity-20" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-muted-foreground">待處理</p>
                    <p className="text-3xl font-bold text-yellow-600">
                      {statistics.pending_questions}
                    </p>
                  </div>
                  <Users className="w-8 h-8 text-yellow-600 opacity-20" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-muted-foreground">已同意</p>
                    <p className="text-3xl font-bold text-green-600">
                      {statistics.approved_questions}
                    </p>
                  </div>
                  <CheckCircle className="w-8 h-8 text-green-600 opacity-20" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Charts */}
          <div className="mb-8">
            <Card>
              <CardHeader>
                <CardTitle>提問狀態分布</CardTitle>
              </CardHeader>
              <CardContent>
                {statusChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={statusChartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, value }) => `${name}: ${value}`}
                        outerRadius={100}
                        dataKey="value"
                      >
                        {statusChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    無資料
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* AI 聚類統計 */}
          {clusters.length > 0 && (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle>AI 聚類分布（前 10 個）</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={clusterChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#0066cc" name="提問數量" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* 匯出功能 */}
          <Card>
            <CardHeader>
              <CardTitle>資料匯出</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleExport("questions")}
                  disabled={exporting === "questions"}
                >
                  <Download className="w-4 h-4 mr-2" />
                  {exporting === "questions" ? "匯出中..." : "匯出提問 CSV"}
                </Button>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleExport("qas")}
                  disabled={exporting === "qas"}
                >
                  <Download className="w-4 h-4 mr-2" />
                  {exporting === "qas" ? "匯出中..." : "匯出 Q&A CSV"}
                </Button>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleExport("statistics")}
                  disabled={exporting === "statistics"}
                >
                  <Download className="w-4 h-4 mr-2" />
                  {exporting === "statistics"
                    ? "匯出中..."
                    : "匯出統計資料 CSV"}
                </Button>
              </div>
              <p className="text-sm text-muted-foreground mt-4">
                當前課程：{selectedCourseName}
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
