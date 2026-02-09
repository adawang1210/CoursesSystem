"use client"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select" // 1. 新增 Select 元件
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis, ComposedChart, Line // 修正圖表引用
} from "recharts"
import { Zap, Download, RefreshCw, AlertCircle, Pencil } from "lucide-react"
import { Slider } from "@/components/ui/slider" // 🔥 新增 Slider
import { Label } from "@/components/ui/label"   // 🔥 新增 Label
import { aiApi, type ClusterSummary } from "@/lib/api/ai"
import { coursesApi, type Course } from "@/lib/api" // 2. 引入 coursesApi
import { useToast } from "@/hooks/use-toast"

export default function ClusteringPage() {
  const [clusters, setClusters] = useState<ClusterSummary[]>([])
  const [courses, setCourses] = useState<Course[]>([]) // 3. 儲存課程列表
  const [selectedCourse, setSelectedCourse] = useState<string>("") // 4. 儲存選中的課程 ID
  const [isLoading, setIsLoading] = useState(false)
  const [isClustering, setIsClustering] = useState(false)
  const { toast } = useToast()
  const [maxClusters, setMaxClusters] = useState<number>(5)

  // 5. 初始載入：先抓課程
  useEffect(() => {
    loadCourses()
  }, [])

  // 6. 當課程改變時，抓取該課程的聚類資料
  useEffect(() => {
    if (selectedCourse) {
      fetchClusters(selectedCourse)
    }
  }, [selectedCourse])

  const loadCourses = async () => {
    try {
      const data = await coursesApi.getAll()
      setCourses(data)
      if (data.length > 0) {
        // 預設選中第一個課程
        setSelectedCourse(data[0]._id || "")
      }
    } catch (error) {
      console.error("無法載入課程", error)
      toast({ title: "錯誤", description: "無法載入課程列表", variant: "destructive" })
    }
  }

  const fetchClusters = async (courseId: string) => {
    setIsLoading(true)
    try {
      const data = await aiApi.getClusters(courseId)
      setClusters(data)
    } catch (error) {
      console.error("無法載入聚類資料", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRunClustering = async () => {
    if (!selectedCourse) {
        toast({ title: "錯誤", description: "請先選擇一個課程", variant: "destructive" })
        return
    }

    setIsClustering(true)
    toast({ title: "AI 分析中", description: `正在執行聚類 (上限 ${maxClusters} 個)，請稍候...` })
    
    try {
      const success = await aiApi.runClustering(selectedCourse, maxClusters)
      if (success) {
        toast({ title: "分析完成", description: "已更新聚類結果" })
        // 稍等一下再重新抓取，確保 DB 寫入完成
        setTimeout(() => fetchClusters(selectedCourse), 1000)
      } else {
        toast({ title: "分析失敗", description: "後端未回傳成功訊號", variant: "destructive" })
      }
    } catch (error) {
      console.error(error)
      toast({ title: "分析錯誤", description: "連線失敗", variant: "destructive" })
    } finally {
      setIsClustering(false)
    }
  }

  // 圖表資料轉換
  const chartData = clusters.map(c => ({
    name: c.topic_label || `主題 ${c.cluster_id.substring(0, 4)}`,
    questions: c.question_count,
    difficulty: Number((c.avg_difficulty || 0).toFixed(2)),
  }))

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold text-foreground mb-2">AI 聚類分析</h1>
          <p className="text-muted-foreground">分析課程的熱門提問主題與難度分佈</p>
        </div>
        
        <div className="flex gap-2 items-center">
            {/* 7. 新增課程選擇下拉選單 */}
            <Select value={selectedCourse} onValueChange={setSelectedCourse}>
                <SelectTrigger className="w-[200px]">
                    <SelectValue placeholder="選擇課程" />
                </SelectTrigger>
                <SelectContent>
                    {courses.map(c => (
                        <SelectItem key={c._id} value={c._id || ""}>{c.course_name}</SelectItem>
                    ))}
                </SelectContent>
            </Select>

            <div className="flex items-center gap-3 px-4 py-2 bg-secondary/20 rounded-md border mr-2">
                <Label className="text-sm whitespace-nowrap text-muted-foreground">
                    分類上限: <span className="font-bold text-foreground">{maxClusters}</span>
                </Label>
                <Slider
                    value={[maxClusters]}
                    onValueChange={(vals) => setMaxClusters(vals[0])}
                    max={15}
                    min={2}
                    step={1}
                    className="w-[100px]"
                />
            </div>

            <Button 
                onClick={() => selectedCourse && fetchClusters(selectedCourse)} 
                variant="outline" 
                size="icon"
                disabled={isLoading || !selectedCourse}
            >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
            <Button onClick={handleRunClustering} disabled={isClustering || !selectedCourse} className="gap-2">
                <Zap className={`w-4 h-4 ${isClustering ? 'animate-pulse' : ''}`} />
                {isClustering ? "分析中..." : "重新運行 AI 分析"}
            </Button>
        </div>
      </div>

      {/* 以下內容保持不變，或根據您的需求顯示 */}
      
      {/* 摘要卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">聚類主題數</p>
            <p className="text-3xl font-bold text-primary">{clusters.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已歸類提問總數</p>
            <p className="text-3xl font-bold text-accent">
              {clusters.reduce((sum, c) => sum + c.question_count, 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">平均難度</p>
            <p className="text-3xl font-bold text-orange-600">
              {clusters.length > 0 
                ? (clusters.reduce((sum, c) => sum + c.avg_difficulty, 0) / clusters.length).toFixed(2) 
                : "0.00"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 若無資料顯示提示 */}
      {clusters.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg bg-secondary/20 mb-8">
              <AlertCircle className="w-10 h-10 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">尚無聚類資料</h3>
              <p className="text-muted-foreground mb-4 text-center max-w-md">
                  目前此課程沒有已分析的聚類結果。可能是因為沒有提問，或者提問尚未進行分析。
                  <br/>請嘗試點擊右上角的「重新運行 AI 分析」。
              </p>
          </div>
      )}

      {/* 圖表區 (有資料才顯示) */}
      {clusters.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <Card>
            <CardHeader>
                <CardTitle>熱門主題排行 (按提問數)</CardTitle>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" />
                    <YAxis dataKey="name" type="category" width={100} tick={{fontSize: 12}} />
                    <Tooltip />
                    <Bar dataKey="questions" fill="#0066cc" name="提問數量" radius={[0, 4, 4, 0]} />
                </BarChart>
                </ResponsiveContainer>
            </CardContent>
            </Card>

            <Card>
            <CardHeader>
                <CardTitle>難度 vs 數量分佈</CardTitle>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" dataKey="questions" name="提問數量" />
                    <YAxis type="number" dataKey="difficulty" name="平均難度" domain={[0, 1]} />
                    <ZAxis type="category" dataKey="name" name="主題" />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                    <Legend />
                    <Scatter name="聚類主題" data={chartData} fill="#ff7300" />
                </ScatterChart>
                </ResponsiveContainer>
            </CardContent>
            </Card>
        </div>
      )}

      {/* 主題詳情列表 */}
      {clusters.length > 0 && (
        <Card>
            <CardHeader>
            <CardTitle>主題詳情列表</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
            {clusters.map((cluster) => (
                <div
                key={cluster.cluster_id}
                className="p-4 border rounded-lg hover:bg-secondary/50 transition-colors relative group"
                >

                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => {
                            toast({ title: "功能開發中", description: `即將編輯: ${cluster.topic_label}` })
                            // 這裡未來會連接到 setEditingCluster(cluster) 與 setIsEditOpen(true)
                        }}>
                            <Pencil className="w-4 h-4 text-muted-foreground" />
                        </Button>
                    </div>

                <div className="flex justify-between items-start mb-2">
                    <div>
                    <h3 className="font-semibold text-lg">
                        {cluster.topic_label || "未命名主題"}
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                        包含 {cluster.question_count} 個提問
                    </p>
                    </div>
                    <div className="text-right">
                    <div className="flex items-center gap-2 mb-1 justify-end">
                        <span className="text-sm text-muted-foreground">平均難度</span>
                        <span className={`text-sm font-bold ${
                        cluster.avg_difficulty > 0.7 ? 'text-red-500' : 
                        cluster.avg_difficulty > 0.4 ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                        {cluster.avg_difficulty.toFixed(2)}
                        </span>
                    </div>
                    </div>
                </div>
                {/* 關鍵字標籤 */}
                <div className="flex flex-wrap gap-2 mt-3">
                    {cluster.top_keywords.map((keyword, idx) => (
                    <span key={idx} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full border border-primary/20">
                        #{keyword}
                    </span>
                    ))}
                </div>
                </div>
            ))}
            </CardContent>
        </Card>
      )}
    </div>
  )
}