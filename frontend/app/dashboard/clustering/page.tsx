"use client"
import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
} from "recharts"
import { Zap, Download } from "lucide-react"

interface Cluster {
  id: string
  name: string
  questionCount: number
  keywords: string[]
  similarity: number
}

const mockClusters: Cluster[] = [
  {
    id: "1",
    name: "Python 基礎語法",
    questionCount: 34,
    keywords: ["變數", "資料型別", "運算符", "控制流"],
    similarity: 0.92,
  },
  {
    id: "2",
    name: "函式和模組",
    questionCount: 28,
    keywords: ["函式定義", "參數", "返回值", "import"],
    similarity: 0.88,
  },
  {
    id: "3",
    name: "資料結構",
    questionCount: 31,
    keywords: ["列表", "字典", "集合", "元組"],
    similarity: 0.85,
  },
  {
    id: "4",
    name: "物件導向設計",
    questionCount: 25,
    keywords: ["類別", "繼承", "多型", "封裝"],
    similarity: 0.81,
  },
]

const clusterStats = [
  { cluster: "基礎語法", questions: 34, trending: 12 },
  { cluster: "函式模組", questions: 28, trending: 8 },
  { cluster: "資料結構", questions: 31, trending: 15 },
  { cluster: "物件導向", questions: 25, trending: 6 },
]

const scatterData = [
  { x: 34, y: 0.92 },
  { x: 28, y: 0.88 },
  { x: 31, y: 0.85 },
  { x: 25, y: 0.81 },
]

export default function ClusteringPage() {
  const [clusters, setClusters] = useState<Cluster[]>(mockClusters)
  const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null)
  const [isClustering, setIsClustering] = useState(false)

  const handleRunClustering = async () => {
    setIsClustering(true)
    // Simulate AI clustering
    await new Promise((resolve) => setTimeout(resolve, 2000))
    setIsClustering(false)
    alert("聚類分析完成")
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold text-foreground mb-2">AI 聚類分析</h1>
          <p className="text-muted-foreground">分析和組織問題聚類</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRunClustering} disabled={isClustering} className="gap-2">
            <Zap className="w-4 h-4" />
            {isClustering ? "分析中..." : "運行聚類"}
          </Button>
          <Button variant="outline" className="gap-2 bg-transparent">
            <Download className="w-4 h-4" />
            匯出報表
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">聚類數量</p>
            <p className="text-3xl font-bold text-primary">{clusters.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">總提問數</p>
            <p className="text-3xl font-bold text-accent">{clusters.reduce((sum, c) => sum + c.questionCount, 0)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">平均相似度</p>
            <p className="text-3xl font-bold text-green-600">
              {(clusters.reduce((sum, c) => sum + c.similarity, 0) / clusters.length).toFixed(2)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">最後更新</p>
            <p className="text-lg font-bold text-blue-600">2024-11-02</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>聚類規模</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={clusterStats}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="cluster" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="questions" fill="#0066cc" name="總提問" />
                <Bar dataKey="trending" fill="#0052a3" name="新增提問" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>相似度分析</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="x" name="提問數量" />
                <YAxis type="number" dataKey="y" name="相似度" />
                <Tooltip />
                <Scatter name="聚類" data={scatterData} fill="#0066cc" />
              </ScatterChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Clusters List */}
      <Card>
        <CardHeader>
          <CardTitle>聚類詳情</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {clusters.map((cluster) => (
            <div
              key={cluster.id}
              onClick={() => setSelectedCluster(cluster)}
              className="p-4 border rounded-lg hover:bg-secondary/50 cursor-pointer transition-colors"
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="font-semibold">{cluster.name}</h3>
                  <p className="text-sm text-muted-foreground">{cluster.questionCount} 個提問</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-primary">相似度: {(cluster.similarity * 100).toFixed(1)}%</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {cluster.keywords.map((keyword, idx) => (
                  <span key={idx} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
