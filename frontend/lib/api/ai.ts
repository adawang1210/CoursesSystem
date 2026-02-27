import { apiClient } from "@/lib/api-client";

// ==================== 資料型別定義 ====================

// 🔥 修正：完美對齊後端 schemas.py 中的 Cluster 模型
export interface ClusterSummary {
  _id?: string;               // MongoDB 的 ID
  course_id: string;          // 課程 ID
  topic_label: string;        // AI 生成的主題標籤
  summary?: string;           // 🔥 新增：該主題的綜合摘要 (AI 生成的解釋)
  keywords: string[];         // 🔥 修正：對應後端的 keywords (原為 top_keywords)
  question_count: number;     // 包含的問題數量
  avg_difficulty: number;     // 平均難度
  is_locked?: boolean;        // 🔥 新增：是否已被人工鎖定
  manual_label?: string;      // 🔥 新增：人工手動設定的標籤名稱
  created_at?: string;
  updated_at?: string;
}

// 通用回應格式
interface APIResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
}

// ==================== API 函式 ====================

export const aiApi = {
  /**
   * 取得課程的 AI 聚類主題牆資料
   * @param courseId 課程 ID
   */
  getClusters: async (courseId: string): Promise<ClusterSummary[]> => {
    console.log(`[aiApi] 正在抓取課程 ${courseId} 的聚類資料...`); 
    
    try {
      const response = await apiClient.get<APIResponse<ClusterSummary[]>>(
        `/ai/clusters/${courseId}`
      );
      
      console.log("[aiApi] 後端回應:", response.data);

      return (response.data as unknown as ClusterSummary[]) || [];
    } catch (error) {
      console.error("Failed to fetch clusters:", error);
      return [];
    }
  },

  /**
   * [手動觸發] 執行課程的聚類分析任務
   * @param courseId 課程 ID
   */
  runClustering: async (courseId: string, maxClusters: number = 5): Promise<boolean> => {
    try {
      await apiClient.post(`/ai/clusters/generate`, { 
        course_id: courseId, 
        max_clusters: maxClusters 
      });
      return true;
    } catch (error) {
      console.error("Failed to trigger clustering:", error);
      return false;
    }
  },

  /**
   * [手動觸發] 為特定問題生成/重寫 AI 回覆草稿
   * @param questionId 問題 ID
   */
  generateDraft: async (questionId: string): Promise<boolean> => {
    try {
      await apiClient.post(`/ai/questions/${questionId}/draft`, {});
      return true;
    } catch (error) {
      console.error("Failed to generate draft:", error);
      return false;
    }
  },

  /**
   * 取得單一問題的 AI 分析結果
   */
  getQuestionAnalysis: async (questionId: string) => {
    try {
      const response = await apiClient.get(`/questions/${questionId}`);
      return response.data;
    } catch (error) {
      return null;
    }
  },

  /**
   * 更新單一聚類資訊
   */
  updateCluster: async (clusterId: string, data: { topic_label?: string; is_locked?: boolean }): Promise<APIResponse<any> | null> => {
    try {
      const response = await apiClient.patch(`/ai/clusters/${clusterId}`, data);
      return response as APIResponse<any>;
    } catch (error) {
      console.error("Failed to update cluster:", error);
      return null;
    }
  },

  /**
   * [新增] 人工手動建立空分類
   * @param courseId 課程 ID
   * @param topicLabel 分類標題
   */
  createCluster: async (courseId: string, topicLabel: string): Promise<APIResponse<any> | null> => {
    try {
      const response = await apiClient.post(`/ai/clusters/manual`, { 
        course_id: courseId, 
        topic_label: topicLabel 
      });
      return response as APIResponse<any>;
    } catch (error) {
      console.error("Failed to create cluster:", error);
      return null;
    }
  },
  
  /**
   * [新增] 刪除分類
   * @param clusterId 分類 ID
   */
  deleteCluster: async (clusterId: string): Promise<APIResponse<any> | null> => {
    try {
      const response = await apiClient.delete(`/ai/clusters/${clusterId}`);
      return response as APIResponse<any>;
    } catch (error) {
      console.error("Failed to delete cluster:", error);
      return null;
    }
  }
};