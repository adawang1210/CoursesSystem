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
} from "@/components/ui/select"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis
} from "recharts"
import { Zap, RefreshCw, AlertCircle, Pencil, Plus, Trash2, Sparkles, Lock } from "lucide-react" 
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input" 
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { aiApi, type ClusterSummary } from "@/lib/api/ai"
import { coursesApi, type Course } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"

export default function ClusteringPage() {
  const [clusters, setClusters] = useState<ClusterSummary[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [selectedCourse, setSelectedCourse] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)
  const [isClustering, setIsClustering] = useState(false)
  const { toast } = useToast()
  const [maxClusters, setMaxClusters] = useState<number>(5)

  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editingCluster, setEditingCluster] = useState<ClusterSummary | null>(null)
  const [editLabel, setEditLabel] = useState("")

  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [addLabel, setAddLabel] = useState("")

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [deletingCluster, setDeletingCluster] = useState<ClusterSummary | null>(null)

  useEffect(() => {
    loadCourses()
  }, [])

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

  const handleSaveEdit = async () => {
    if (!editingCluster || !editingCluster._id || !editLabel.trim()) return
    
    const targetId = editingCluster._id // 🔥 修正為 _id
    const newLabel = editLabel.trim()

    const res = await aiApi.updateCluster(targetId, { 
      topic_label: newLabel, 
      is_locked: true 
    })
    
    if (res?.success) {
      toast({ title: "更新成功", description: "分類標題已修改" })
      setIsEditDialogOpen(false)
      
      setClusters(prevClusters => 
        prevClusters.map(c => 
          c._id === targetId // 🔥 修正為 _id
            ? { ...c, topic_label: newLabel, is_locked: true } 
            : c
        )
      )
      
      setEditingCluster(null)
    } else {
      toast({ title: "更新失敗", description: res?.message || "發生錯誤", variant: "destructive" })
    }
  }

  const handleAddNewCluster = async () => {
    if (!selectedCourse || !addLabel.trim()) return
    
    const newLabel = addLabel.trim()

    const res = await aiApi.createCluster(selectedCourse, newLabel)
    if (res?.success) {
      toast({ title: "新增成功", description: `已建立「${newLabel}」分類` })
      setIsAddDialogOpen(false)
      setAddLabel("") 
      
      setClusters(prevClusters => [
        ...prevClusters,
        {
          _id: `temp-${Date.now()}`, // 🔥 修正為 _id
          course_id: selectedCourse,
          topic_label: newLabel,
          question_count: 0,
          avg_difficulty: 0,
          keywords: [] 
        }
      ])

      fetchClusters(selectedCourse) 
    } else {
      toast({ title: "新增失敗", description: res?.message || "發生錯誤", variant: "destructive" })
    }
  }

  const handleDeleteCluster = async () => {
    if (!deletingCluster || !deletingCluster._id) return
    
    const targetId = deletingCluster._id; // 🔥 修正為 _id
    
    const res = await aiApi.deleteCluster(targetId)
    if (res?.success) {
      toast({ title: "刪除成功", description: "分類已移除，內部問題已釋放" })
      setIsDeleteDialogOpen(false)
      
      setClusters(prevClusters => prevClusters.filter(c => c._id !== targetId)) // 🔥 修正為 _id
      
      setDeletingCluster(null)
    } else {
      toast({ title: "刪除失敗", description: res?.message || "發生錯誤", variant: "destructive" })
    }
  }

  const chartData = clusters.map(c => ({
    name: c.topic_label || `主題 ${c._id?.substring(0, 4)}`, // 🔥 修正為 _id
    questions: c.question_count,
    difficulty: Number((c.avg_difficulty || 0).toFixed(2)),
  }))

  return (
    <div className="p-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-4xl font-bold text-foreground mb-2">AI 聚類分析</h1>
          <p className="text-muted-foreground">分析課程的熱門提問主題與難度分佈</p>
        </div>
        
        <div className="flex flex-wrap gap-2 items-center w-full md:w-auto">
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

            <div className="flex items-center gap-3 px-4 py-2 bg-secondary/20 rounded-md border">
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

            <Button variant="outline" onClick={() => setIsAddDialogOpen(true)} disabled={!selectedCourse}>
              <Plus className="w-4 h-4 mr-2" />
              新增分類
            </Button>

            <Button onClick={handleRunClustering} disabled={isClustering || !selectedCourse} className="gap-2">
                <Zap className={`w-4 h-4 ${isClustering ? 'animate-pulse' : ''}`} />
                {isClustering ? "分析中..." : "重新運行 AI 分析"}
            </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
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

      {clusters.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg bg-secondary/20 mb-8">
              <AlertCircle className="w-10 h-10 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">尚無聚類資料</h3>
              <p className="text-muted-foreground mb-4 text-center max-w-md">
                  目前此課程沒有已分析的聚類結果。
                  <br/>您可以點擊「新增分類」手動建立，或點擊「重新運行 AI 分析」。
              </p>
          </div>
      )}

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

      {clusters.length > 0 && (
        <Card>
            <CardHeader>
            <CardTitle>主題詳情列表</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
            {clusters.map((cluster, index) => (
                <div
                // 🔥 加上萬用備案：不管後端傳哪種 ID 名稱都抓得到，最糟的情況下使用 index
                key={cluster._id || (cluster as any).id || (cluster as any).cluster_id || `cluster-${index}`}
                className="p-4 border rounded-lg hover:bg-secondary/50 transition-colors relative group"
                >
                    <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => {
                            setEditingCluster(cluster)
                            setEditLabel(cluster.topic_label || "")
                            setIsEditDialogOpen(true)
                        }}>
                            <Pencil className="w-4 h-4 text-muted-foreground" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive" onClick={() => {
                            setDeletingCluster(cluster)
                            setIsDeleteDialogOpen(true)
                        }}>
                            <Trash2 className="w-4 h-4" />
                        </Button>
                    </div>

                    <div className="flex justify-between items-start mb-2">
                        <div>
                        <h3 className="font-semibold text-lg flex items-center gap-2">
                          {cluster.topic_label || "未命名主題"}
                          {cluster.is_locked && (
                              <span title="已人工鎖定，AI重新聚類時不會被覆寫" className="flex items-center">
                                 <Lock className="w-4 h-4 text-muted-foreground" />
                              </span>
                          )}
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
                    
                    {cluster.summary && (
                      <p className="text-sm text-muted-foreground mt-3 mb-2 p-3 bg-secondary/30 rounded-md border border-border/50">
                        <Sparkles className="w-3 h-3 inline mr-1 text-indigo-500" />
                        {cluster.summary}
                      </p>
                    )}

                    <div className="flex flex-wrap gap-2 mt-3">
                        {cluster.keywords?.map((keyword, idx) => (
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

      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>修改分類名稱</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="edit-name">分類名稱</Label>
            <Input 
              id="edit-name" 
              value={editLabel} 
              onChange={(e) => setEditLabel(e.target.value)} 
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveEdit}>儲存並鎖定</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>手動新增分類</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="add-name">新分類名稱</Label>
            <Input 
              id="add-name" 
              placeholder="例如：行政規定、作業繳交..."
              value={addLabel} 
              onChange={(e) => setAddLabel(e.target.value)} 
              className="mt-2"
            />
            <p className="text-sm text-muted-foreground mt-2">
              手動建立的分類將保留於系統中，下次執行 AI 聚類時，AI 將優先將相似問題歸入此分類。
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>取消</Button>
            <Button onClick={handleAddNewCluster}>新增</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive">刪除分類確認</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p>確定要刪除「<strong>{deletingCluster?.topic_label}</strong>」這個分類嗎？</p>
            <p className="text-sm text-muted-foreground mt-2">
              刪除後，該分類內的 <strong>{deletingCluster?.question_count}</strong> 個提問將會被恢復成「未分類」狀態，下次執行 AI 聚類時將由 AI 重新分配。
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteCluster}>確認刪除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}