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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  BarChart,
  Bar,
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
  MessageSquare,
  Download,
  RefreshCw,
  TrendingUp, 
  Network
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
  
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [selectedClass, setSelectedClass] = useState<string>("");
  
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
      const activeCourses = coursesData.filter(c => c.is_active);
      if (activeCourses.length > 0) {
        setCourses(activeCourses);
        setSelectedCourse(activeCourses[0]._id || "");
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

  const handleExport = async (type: "questions" | "qas" | "statistics" | "clusters") => {
    if (!selectedCourse) return;

    try {
      setExporting(type);
      let blob: Blob;

      const baseParams: any = { 
        course_id: selectedCourse,
        start_date: startDate || undefined,
        end_date: endDate || undefined
      };

      if (selectedClass) baseParams.class_id = selectedClass;

      switch (type) {
        case "questions":
          blob = await reportsApi.exportQuestions(baseParams);
          break;
        case "qas":
          blob = await reportsApi.exportQAs(baseParams);
          break;
        case "statistics":
          blob = await reportsApi.exportStatistics(baseParams);
          break;
        case "clusters": 
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
    <div className="p-8 max-w-7xl mx-auto">
       <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">任務學習成效報表</h1>
        <p className="text-muted-foreground">分析學生在課後 Q&A 任務中的作答狀況與學習難點</p>
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
          {/* 🔥 數據卡片區塊重構 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"> 
            <Card>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">總收集回覆數</p>
                    <p className="text-4xl font-bold text-primary mt-2">{statistics.total_questions}</p>
                  </div>
                  <div className="p-3 bg-primary/10 rounded-lg">
                    <MessageSquare className="w-6 h-6 text-primary" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">AI 批閱群組數</p>
                    <p className="text-4xl font-bold text-indigo-600 mt-2">{clusters.length}</p>
                  </div>
                  <div className="p-3 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
                    <Network className="w-6 h-6 text-indigo-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">整體平均難度</p>
                    <p className="text-4xl font-bold text-orange-500 mt-2">
                      {statistics.avg_difficulty_score?.toFixed(2) || "0.00"}
                    </p>
                  </div>
                  <div className="p-3 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                    <TrendingUp className="w-6 h-6 text-orange-500" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 🔥 圖表區塊重構 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <Card>
              <CardHeader><CardTitle>學生學習難度分布</CardTitle></CardHeader>
              <CardContent>
                 <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={difficultyChartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} />
                    <YAxis axisLine={false} tickLine={false} />
                    <Tooltip cursor={{fill: 'transparent'}} />
                    <Bar dataKey="value" name="回覆數量" radius={[4, 4, 0, 0]} maxBarSize={60}>
                      {difficultyChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>前 10 大熱門批閱主題與難度</CardTitle></CardHeader>
              <CardContent>
                {clusters.length > 0 ? (
                  <ResponsiveContainer width="100%" height={320}>
                    <ComposedChart data={clusterChartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" scale="band" axisLine={false} tickLine={false} tick={{fontSize: 12}} />
                      <YAxis yAxisId="left" axisLine={false} tickLine={false} />
                      <YAxis yAxisId="right" orientation="right" domain={[0, 1]} axisLine={false} tickLine={false} />
                      <Tooltip />
                      <Legend wrapperStyle={{ paddingTop: '20px' }} />
                      <Bar yAxisId="left" dataKey="count" fill="#4f46e5" name="包含回覆數" radius={[4, 4, 0, 0]} maxBarSize={40} />
                      <Line yAxisId="right" type="monotone" dataKey="difficulty" stroke="#f97316" name="主題平均難度" strokeWidth={3} dot={{r: 4}} />
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[320px] flex items-center justify-center text-muted-foreground border-2 border-dashed rounded-lg">
                    目前尚無 AI 聚類資料
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>資料匯出與過濾設定</CardTitle></CardHeader>
            <CardContent>
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

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4"> 
                <Button variant="outline" onClick={() => handleExport("questions")} disabled={exporting === "questions"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出原始作答明細
                </Button>
                <Button variant="outline" onClick={() => handleExport("qas")} disabled={exporting === "qas"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出 Q&A 完整紀錄
                </Button>
                <Button variant="outline" onClick={() => handleExport("statistics")} disabled={exporting === "statistics"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出成效統計
                </Button>
                <Button variant="outline" onClick={() => handleExport("clusters")} disabled={exporting === "clusters"}>
                  <Download className="w-4 h-4 mr-2" /> 匯出 AI 批閱分析
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