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
  ComposedChart, // 1. 新增 ComposedChart
  Line,          // 1. 新增 Line
} from "recharts";
import {
  Users,
  MessageSquare,
  CheckCircle,
  Download,
  RefreshCw,
  TrendingUp, // 2. 新增圖示
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

  // ... (loadCourses, loadStatistics, loadClusters 邏輯保持不變) ...

  useEffect(() => {
    loadCourses();
  }, []);

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
    }
  };

  const loadStatistics = async () => {
    if (!selectedCourse) return;
    try {
      setLoading(true);
      const response = await reportsApi.getStatistics({ course_id: selectedCourse });
      if (response.success) setStatistics(response.data ?? null);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadClusters = async () => {
    if (!selectedCourse) return;
    try {
      const response = await reportsApi.getClustersSummary(selectedCourse);
      if (response.success) setClusters(response.data ?? []);
    } catch (error) {
      console.error(error);
    }
  };

  // 3. 修改匯出邏輯，支援 'clusters'
  const handleExport = async (type: "questions" | "qas" | "statistics" | "clusters") => {
    if (!selectedCourse) return;

    try {
      setExporting(type);
      let blob: Blob;

      switch (type) {
        case "questions":
          blob = await reportsApi.exportQuestions({ course_id: selectedCourse });
          break;
        case "qas":
          blob = await reportsApi.exportQAs({ course_id: selectedCourse });
          break;
        case "statistics":
          blob = await reportsApi.exportStatistics({ course_id: selectedCourse });
          break;
        case "clusters": // 新增匯出選項
          // 注意：需確認 reportsApi 有實作 exportClusters
          // 若無，請在 frontend/lib/api/reports.ts 補上
          blob = await reportsApi.exportClusters({ course_id: selectedCourse });
          break;
      }

      const url = window.URL.createObjectURL(blob!); // 加 ! 忽略 TS 檢查，實務上 blob 一定有值
      const a = document.createElement("a");
      a.href = url;
      a.download = `${type}_${selectedCourse}_${new Date().getTime()}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({ title: "成功", description: "資料匯出成功" });
    } catch (error) {
      console.error("匯出失敗:", error);
      toast({ title: "錯誤", description: "匯出資料失敗", variant: "destructive" });
    } finally {
      setExporting(null);
    }
  };

  // ... (statusChartData 保持不變) ...
  const statusChartData = statistics?.status_distribution
    ? Object.entries(statistics.status_distribution).map(([status, count]) => ({
        name: getStatusLabel(status),
        value: count,
        fill: getStatusColor(status),
      }))
    : [];

  // 4. 新增難度分佈資料準備
  const difficultyChartData = statistics?.difficulty_distribution
    ? [
        { name: "簡單", value: statistics.difficulty_distribution.easy || 0, fill: "#22c55e" },
        { name: "中等", value: statistics.difficulty_distribution.medium || 0, fill: "#eab308" },
        { name: "困難", value: statistics.difficulty_distribution.hard || 0, fill: "#ef4444" },
      ]
    : [];

  const clusterChartData = clusters.slice(0, 10).map((cluster) => ({
    name: cluster.topic_label || `主題 ${cluster.cluster_id.substring(0, 4)}`, // 優先顯示主題標籤
    count: cluster.question_count,
    difficulty: Number((cluster.avg_difficulty || 0).toFixed(2)), // 轉為數字供圖表使用
  }));

  function getStatusLabel(status: string) { /* ... 保持不變 ... */ return status; }
  function getStatusColor(status: string) { /* ... 保持不變 ... */ return "#9ca3af"; }

  const selectedCourseName = courses.find((c) => c._id === selectedCourse)?.course_name || "";

  return (
    <div className="p-8">
      {/* ... (標題與篩選器保持不變) ... */}
       <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">統計報表</h1>
        <p className="text-muted-foreground">查看平台統計數據和分析</p>
      </div>

      <div className="mb-6 flex items-center gap-4">
        {/* ... Select 元件保持不變 ... */}
        <div className="flex-1 max-w-md">
            <Select value={selectedCourse} onValueChange={setSelectedCourse}>
            <SelectTrigger><SelectValue placeholder="選擇課程" /></SelectTrigger>
            <SelectContent>
                {courses.map(c => <SelectItem key={c._id} value={c._id || ""}>{c.course_name}</SelectItem>)}
            </SelectContent>
            </Select>
        </div>
         <Button variant="outline" size="icon" onClick={() => { loadStatistics(); loadClusters(); }} disabled={loading || !selectedCourse}>
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
         </Button>
      </div>

      {!selectedCourse ? ( /* ... */ <div/> ) : loading ? ( /* ... */ <div/> ) : !statistics ? ( /* ... */ <div/> ) : (
        <>
          {/* KPI Cards: 新增平均難度 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8"> {/* 改成 4 欄 */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-muted-foreground">總提問數</p>
                    <p className="text-3xl font-bold text-primary">{statistics.total_questions}</p>
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
                    <p className="text-3xl font-bold text-yellow-600">{statistics.pending_questions}</p>
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
                    <p className="text-3xl font-bold text-green-600">{statistics.approved_questions}</p>
                  </div>
                  <CheckCircle className="w-8 h-8 text-green-600 opacity-20" />
                </div>
              </CardContent>
            </Card>
            {/* 新增：平均難度卡片 */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-muted-foreground">平均難度</p>
                    <p className="text-3xl font-bold text-orange-500">
                      {statistics.avg_difficulty_score?.toFixed(2) || "0.00"}
                    </p>
                  </div>
                  <TrendingUp className="w-8 h-8 text-orange-500 opacity-20" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Charts: 新增難度分佈 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <Card>
              <CardHeader><CardTitle>提問狀態分布</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={statusChartData} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name}: ${value}`} outerRadius={100} dataKey="value">
                      {statusChartData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* 新增：難度分佈圖表 */}
            <Card>
              <CardHeader><CardTitle>問題難度分布</CardTitle></CardHeader>
              <CardContent>
                 <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={difficultyChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" name="數量" radius={[4, 4, 0, 0]}>
                      {difficultyChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* AI 聚類統計：改為複合圖表 (數量+難度) */}
          {clusters.length > 0 && (
            <Card className="mb-8">
              <CardHeader><CardTitle>熱門主題與難度分析（前 10 個）</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={clusterChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" scale="band" />
                    <YAxis yAxisId="left" label={{ value: '提問數', angle: -90, position: 'insideLeft' }} />
                    <YAxis yAxisId="right" orientation="right" domain={[0, 1]} label={{ value: '難度', angle: 90, position: 'insideRight' }} />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="count" fill="#0066cc" name="提問數量" barSize={40} />
                    <Line yAxisId="right" type="monotone" dataKey="difficulty" stroke="#ff7300" name="平均難度" strokeWidth={2} />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* 匯出功能：新增匯出主題按鈕 */}
          <Card>
            <CardHeader><CardTitle>資料匯出</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4"> {/* 改成 4 欄 */}
                <Button variant="outline" onClick={() => handleExport("questions")} disabled={exporting === "questions"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出提問 CSV
                </Button>
                <Button variant="outline" onClick={() => handleExport("qas")} disabled={exporting === "qas"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出 Q&A CSV
                </Button>
                <Button variant="outline" onClick={() => handleExport("statistics")} disabled={exporting === "statistics"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出統計資料
                </Button>
                {/* 新增按鈕 */}
                <Button variant="outline" onClick={() => handleExport("clusters")} disabled={exporting === "clusters"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出主題分析
                </Button>
              </div>
              <p className="text-sm text-muted-foreground mt-4">當前課程：{selectedCourseName}</p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}