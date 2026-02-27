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
// 🔥 新增匯入 Input 與 Label 元件，用於過濾器
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  ComposedChart, 
  Line,          
} from "recharts";
import {
  Users,
  MessageSquare,
  CheckCircle,
  Download,
  RefreshCw,
  TrendingUp, 
} from "lucide-react";
import {
  reportsApi,
  coursesApi,
  type Statistics,
  type Course,
} from "@/lib/api";
import { type ClusterSummary } from "@/lib/api/ai";
import { useToast } from "@/hooks/use-toast";

export default function StatisticsPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>("");
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  
  // =========== 🔥 新增：多維度過濾器狀態 ===========
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [selectedClass, setSelectedClass] = useState<string>("");
  // ==============================================
  
  const { toast } = useToast();

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
      const coursesData = await coursesApi.getAll();
      if (coursesData.length > 0) {
        setCourses(coursesData);
        setSelectedCourse(coursesData[0]._id || "");
      }
    } catch (error) {
      console.error("載入課程失敗:", error);
      toast({ title: "錯誤", description: "載入課程失敗", variant: "destructive" });
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
      toast({ title: "錯誤", description: "載入統計資料失敗", variant: "destructive" });
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

  // 🔥 修正：將過濾條件 (startDate, endDate, selectedClass) 帶入 API 呼叫中
  const handleExport = async (type: "questions" | "qas" | "statistics" | "clusters") => {
    if (!selectedCourse) return;

    try {
      setExporting(type);
      let blob: Blob;

      // 準備基礎參數
      const baseParams: any = { course_id: selectedCourse };
      if (selectedClass) baseParams.class_id = selectedClass;

      switch (type) {
        case "questions":
          blob = await reportsApi.exportQuestions({ 
            ...baseParams,
            start_date: startDate || undefined,
            end_date: endDate || undefined
          });
          break;
        case "qas":
          blob = await reportsApi.exportQAs(baseParams);
          break;
        case "statistics":
          blob = await reportsApi.exportStatistics(baseParams);
          break;
        case "clusters": 
          // 主題聚類通常是看整體的，故只傳入 course_id
          blob = await reportsApi.exportClusters({ course_id: selectedCourse });
          break;
      }

      const url = window.URL.createObjectURL(blob!); 
      const a = document.createElement("a");
      a.href = url;
      a.download = `${type}_${selectedCourse}_${new Date().getTime()}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({ title: "成功", description: "資料匯出成功！" });
    } catch (error) {
      console.error("匯出失敗:", error);
      toast({ title: "錯誤", description: "匯出資料失敗", variant: "destructive" });
    } finally {
      setExporting(null);
    }
  };

  function getStatusLabel(status: string) {
    switch (status.toUpperCase()) {
      case "PENDING": return "待處理";
      case "APPROVED": return "已同意";
      case "REJECTED": return "已拒絕";
      case "DELETED": return "已刪除";
      default: return status;
    }
  }

  function getStatusColor(status: string) {
    switch (status.toUpperCase()) {
      case "PENDING": return "#eab308"; 
      case "APPROVED": return "#22c55e"; 
      case "REJECTED": return "#ef4444"; 
      case "DELETED": return "#6b7280"; 
      default: return "#9ca3af";
    }
  }

  const statusChartData = statistics?.status_distribution
    ? Object.entries(statistics.status_distribution).map(([status, count]) => ({
        name: getStatusLabel(status),
        value: count,
        fill: getStatusColor(status),
      }))
    : [];

  const difficultyChartData = statistics?.difficulty_distribution
    ? [
        { name: "簡單", value: statistics.difficulty_distribution.easy || 0, fill: "#22c55e" },
        { name: "中等", value: statistics.difficulty_distribution.medium || 0, fill: "#eab308" },
        { name: "困難", value: statistics.difficulty_distribution.hard || 0, fill: "#ef4444" },
      ]
    : [];

  const clusterChartData = clusters.slice(0, 10).map((cluster: any) => ({
    name: cluster.topic_label || `主題 ${String(cluster._id || cluster.cluster_id || "").substring(0, 4)}`, 
    count: cluster.question_count || 0,
    difficulty: Number((cluster.avg_difficulty || 0).toFixed(2)), 
  }));

  const selectedCourseName = courses.find((c) => c._id === selectedCourse)?.course_name || "";

  return (
    <div className="p-8">
       <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">統計報表</h1>
        <p className="text-muted-foreground">查看平台統計數據和分析</p>
      </div>

      <div className="mb-6 flex items-center gap-4">
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

      {!selectedCourse ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">請選擇課程以查看統計報表</CardContent></Card>
      ) : loading ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">資料載入中，請稍候...</CardContent></Card>
      ) : !statistics ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">目前該課程尚無足夠的統計資料</CardContent></Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8"> 
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

          <Card>
            <CardHeader><CardTitle>資料匯出與過濾設定</CardTitle></CardHeader>
            <CardContent>
              {/* =========== 🔥 新增：過濾器 UI 區塊 =========== */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 p-4 bg-secondary/20 rounded-lg border">
                <div>
                  <Label className="mb-2 block text-sm font-medium">班級 / 分組過濾 (可留空)</Label>
                  <Input 
                    placeholder="輸入班級或分組代號" 
                    value={selectedClass} 
                    onChange={(e) => setSelectedClass(e.target.value)} 
                  />
                </div>
                <div>
                  <Label className="mb-2 block text-sm font-medium">開始日期 (可留空)</Label>
                  <Input 
                    type="date" 
                    value={startDate} 
                    onChange={(e) => setStartDate(e.target.value)} 
                  />
                </div>
                <div>
                  <Label className="mb-2 block text-sm font-medium">結束日期 (可留空)</Label>
                  <Input 
                    type="date" 
                    value={endDate} 
                    onChange={(e) => setEndDate(e.target.value)} 
                  />
                </div>
              </div>
              {/* ============================================== */}

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4"> 
                <Button variant="outline" onClick={() => handleExport("questions")} disabled={exporting === "questions"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出提問 CSV
                </Button>
                <Button variant="outline" onClick={() => handleExport("qas")} disabled={exporting === "qas"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出 Q&A CSV
                </Button>
                <Button variant="outline" onClick={() => handleExport("statistics")} disabled={exporting === "statistics"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出統計資料
                </Button>
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