"use client"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
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
import { Zap, RefreshCw, AlertCircle, Pencil, Plus, Trash2, Sparkles, Lock, MessageCircle } from "lucide-react" 
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
import { coursesApi, qasApi, type Course } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"

export default function ClusteringPage() {
  const [clusters, setClusters] = useState<ClusterSummary[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  
  // 🔥 狀態管理：目前選擇的課程與 Q&A 模式 (移除 GENERAL 預設值)
  const [selectedCourse, setSelectedCourse] = useState<string>("")
  const [qasList, setQasList] = useState<any[]>([])
  const [selectedQaId, setSelectedQaId] = useState<string>("") // 預設為空字串
  
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

  // 1. 載入課程
  useEffect(() => {
    const loadCourses = async () => {
      try {
        const data = await coursesApi.getAll()
        setCourses(data)
        if (data.length > 0) {
          setSelectedCourse(data[0]._id || "")
        }
      } catch (error) {
        toast({ title: "錯誤", description: "無法載入課程列表", variant: "destructive" })
      }
    }
    loadCourses()
  }, [])

  // 2. 當課程改變時，載入該課程的 Q&A 列表 (只抓有開啟互動的)
  useEffect(() => {
    if (!selectedCourse) return

    const fetchQAs = async () => {
      try {
        const qas = await qasApi.getAll({ course_id: selectedCourse })
        // 只保留有開啟互動的 Q&A 作為批閱選項
        const interactiveQAs = qas.filter((qa: any) => qa.allow_replies)
        setQasList(interactiveQAs)
        
        // 🔥 自動預設選中第一筆 Q&A
        if (interactiveQAs.length > 0) {
            setSelectedQaId(interactiveQAs[0]._id)
        } else {
            setSelectedQaId("")
        }
      } catch (error) {
        console.error("無法載入 Q&A 列表", error)
      }
    }
    
    fetchQAs()
  }, [selectedCourse])

  // 3. 當課程或 QA 選項改變時，載入對應的聚類資料
  useEffect(() => {
    if (!selectedCourse || !selectedQaId) {
        setClusters([]) // 若無選擇 QA，清空結果
        return
    }
    
    const fetchClustersData = async () => {
      setIsLoading(true)
      try {
        // 🔥 確保傳入 selectedQaId
        const data = await aiApi.getClusters(selectedCourse, selectedQaId)
        setClusters(data)
      } catch (error) {
        console.error("無法載入聚類資料", error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchClustersData()
  }, [selectedCourse, selectedQaId])

  // 🔥 觸發 AI 分析 (專注於批閱模式)
  const handleRunClustering = async () => {
    if (!selectedCourse || !selectedQaId) return

    setIsClustering(true)
    
    toast({ 
      title: "AI 分析中", 
      description: `正在批閱學生的回答 (上限 ${maxClusters} 個群組)...` 
    })
    
    try {
      const success = await aiApi.runClustering(selectedCourse, maxClusters, selectedQaId)
      if (success) {
        toast({ title: "分析完成", description: "已更新聚類結果" })
        setTimeout(async () => {
          const data = await aiApi.getClusters(selectedCourse, selectedQaId)
          setClusters(data)
        }, 1500)
      } else {
        toast({ title: "分析失敗", description: "後端未回傳成功訊號", variant: "destructive" })
      }
    } catch (error) {
      toast({ title: "分析錯誤", description: "連線失敗", variant: "destructive" })
    } finally {
      setIsClustering(false)
    }
  }

  const handleSaveEdit = async () => {
    if (!editingCluster || !editingCluster._id || !editLabel.trim()) return
    
    const targetId = editingCluster._id 
    const newLabel = editLabel.trim()

    const res = await aiApi.updateCluster(targetId, { topic_label: newLabel, is_locked: true })
    
    if (res?.success) {
      toast({ title: "更新成功", description: "分類標題已修改" })
      setIsEditDialogOpen(false)
      setClusters(prev => prev.map(c => c._id === targetId ? { ...c, topic_label: newLabel, is_locked: true } : c))
      setEditingCluster(null)
    } else {
      toast({ title: "更新失敗", description: res?.message || "發生錯誤", variant: "destructive" })
    }
  }

  const handleAddNewCluster = async () => {
    if (!selectedCourse || !addLabel.trim() || !selectedQaId) return
    
    const newLabel = addLabel.trim()

    const res = await aiApi.createCluster(selectedCourse, newLabel, selectedQaId)
    if (res?.success) {
      toast({ title: "新增成功", description: `已建立「${newLabel}」分類` })
      setIsAddDialogOpen(false)
      setAddLabel("") 
      const data = await aiApi.getClusters(selectedCourse, selectedQaId)
      setClusters(data)
    } else {
      toast({ title: "新增失敗", description: res?.message || "發生錯誤", variant: "destructive" })
    }
  }

  const handleDeleteCluster = async () => {
    if (!deletingCluster || !deletingCluster._id) return
    
    const targetId = deletingCluster._id
    
    const res = await aiApi.deleteCluster(targetId)
    if (res?.success) {
      toast({ title: "刪除成功", description: "分類已移除，內部問題已釋放" })
      setIsDeleteDialogOpen(false)
      setClusters(prev => prev.filter(c => c._id !== targetId)) 
      setDeletingCluster(null)
    } else {
      toast({ title: "刪除失敗", description: res?.message || "發生錯誤", variant: "destructive" })
    }
  }

  const chartData = clusters.map(c => ({
    name: c.topic_label || `主題 ${c._id?.substring(0, 4)}`,
    questions: c.question_count,
    difficulty: Number((c.avg_difficulty || 0).toFixed(2)),
  }))

  // 取得目前選中的 Q&A 詳細資訊
  const currentQAInfo = qasList.find(qa => qa._id === selectedQaId)

  return (
    <div className="p-8">
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-8 gap-4">
        <div>
          <h1 className="text-4xl font-bold text-foreground mb-2">AI 聚類分析</h1>
          <p className="text-muted-foreground">批閱並分類課後 Q&A 的學生回答</p>
        </div>
        
        <div className="flex flex-wrap gap-2 items-center w-full xl:w-auto bg-secondary/10 p-2 rounded-lg border border-border/50">
            {/* 課程選擇 */}
            <Select value={selectedCourse} onValueChange={setSelectedCourse}>
                <SelectTrigger className="w-[180px] bg-background">
                    <SelectValue placeholder="選擇課程" />
                </SelectTrigger>
                <SelectContent>
                    {courses.map(c => (
                        <SelectItem key={c._id} value={c._id || ""}>{c.course_name}</SelectItem>
                    ))}
                </SelectContent>
            </Select>

            {/* 🔥 修改：移除一般提問選項，只留下 Q&A */}
            <Select value={selectedQaId} onValueChange={setSelectedQaId} disabled={qasList.length === 0}>
                <SelectTrigger className="w-[280px] bg-background border-indigo-200">
                    <SelectValue placeholder={qasList.length === 0 ? "尚無 Q&A 紀錄" : "選擇要批閱的 Q&A"} />
                </SelectTrigger>
                <SelectContent>
                    {qasList.map((qa) => (
                        <SelectItem key={qa._id} value={qa._id || ""}>
                          📝 {qa.question.length > 15 ? qa.question.substring(0, 15) + '...' : qa.question}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>

            <div className="flex items-center gap-3 px-4 py-2 bg-background rounded-md border">
                <Label className="text-sm whitespace-nowrap text-muted-foreground">
                    分群上限: <span className="font-bold text-foreground">{maxClusters}</span>
                </Label>
                <Slider
                    value={[maxClusters]}
                    onValueChange={(vals) => setMaxClusters(vals[0])}
                    max={15}
                    min={2}
                    step={1}
                    className="w-[80px]"
                />
            </div>

            <Button 
                onClick={() => selectedCourse && selectedQaId && aiApi.getClusters(selectedCourse, selectedQaId).then(setClusters)} 
                variant="outline" 
                size="icon"
                disabled={isLoading || !selectedCourse || !selectedQaId}
                className="bg-background"
            >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>

            <Button onClick={handleRunClustering} disabled={isClustering || !selectedCourse || !selectedQaId} className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white">
                <Zap className={`w-4 h-4 ${isClustering ? 'animate-pulse' : ''}`} />
                {isClustering ? "批閱中..." : "批閱學生回答"}
            </Button>
        </div>
      </div>

      {/* 🔥 顯示題目資訊面板 */}
      {selectedQaId && currentQAInfo && (
        <Card className="mb-8 border-indigo-200 dark:border-indigo-900 shadow-sm bg-indigo-50/30 dark:bg-indigo-950/10">
           <CardHeader className="pb-3">
             <CardTitle className="text-lg flex items-center text-indigo-700 dark:text-indigo-400">
               <MessageCircle className="w-5 h-5 mr-2" /> 
               批閱基準與題目資訊
             </CardTitle>
           </CardHeader>
           <CardContent>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <p className="text-xs uppercase font-bold text-muted-foreground mb-1">老師的提問</p>
                  <p className="text-sm p-3 bg-background rounded-md border">{currentQAInfo.question}</p>
                </div>
                <div>
                  <p className="text-xs uppercase font-bold text-muted-foreground mb-1">標準解答 / 評分基準</p>
                  <p className="text-sm p-3 bg-background rounded-md border whitespace-pre-wrap">{currentQAInfo.answer}</p>
                </div>
             </div>
           </CardContent>
        </Card>
      )}

      {/* 以下圖表與列表保持原樣... */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">分群數量</p>
            <p className="text-3xl font-bold text-primary">{clusters.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已歸類總數</p>
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
                  目前此題目還沒有被 AI 批閱過。請確保有學生回答後，點擊「批閱學生回答」。
              </p>
          </div>
      )}

      {clusters.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <Card>
            <CardHeader>
                <CardTitle>各群組人數分佈</CardTitle>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" />
                    <YAxis dataKey="name" type="category" width={120} tick={{fontSize: 12}} />
                    <Tooltip />
                    <Bar dataKey="questions" fill="#4f46e5" name="包含數量" radius={[0, 4, 4, 0]} />
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
                    <XAxis type="number" dataKey="questions" name="數量" />
                    <YAxis type="number" dataKey="difficulty" name="平均難度" domain={[0, 1]} />
                    <ZAxis type="category" dataKey="name" name="主題" />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                    <Legend />
                    <Scatter name="群組" data={chartData} fill="#ff7300" />
                </ScatterChart>
                </ResponsiveContainer>
            </CardContent>
            </Card>
        </div>
      )}

      {clusters.length > 0 && (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>群組詳細批閱結果</CardTitle>
              <Button variant="outline" size="sm" onClick={() => setIsAddDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" /> 新增分類
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
            {clusters.map((cluster, index) => (
                <div
                key={cluster._id || `cluster-${index}`}
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
                            包含 {cluster.question_count} 個作答/提問
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
                      <div className="mt-3 mb-2 p-3 bg-secondary/30 rounded-md border border-border/50">
                        <p className="text-sm font-medium text-foreground flex items-center mb-1">
                          <Sparkles className="w-3 h-3 mr-1 text-indigo-500" />
                          AI 批閱總結
                        </p>
                        <p className="text-sm text-muted-foreground">{cluster.summary}</p>
                      </div>
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
            <Input id="edit-name" value={editLabel} onChange={(e) => setEditLabel(e.target.value)} className="mt-2" />
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
            <Input id="add-name" placeholder="例如：完全正確、觀念混淆..." value={addLabel} onChange={(e) => setAddLabel(e.target.value)} className="mt-2" />
            <p className="text-sm text-muted-foreground mt-2">
              手動建立的分類將保留於系統中，下次執行 AI 聚類時，AI 將優先將相似作答歸入此分類。
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
              刪除後，該分類內的作答將會被恢復成「未分類」狀態，下次執行 AI 聚類時將由 AI 重新分配。
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