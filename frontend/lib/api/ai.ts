import { apiClient } from "@/lib/api-client";

// ==================== 資料型別定義 ====================

// 對應後端回傳的聚類摘要格式
export interface ClusterSummary {
  cluster_id: string;
  topic_label?: string; 
  question_count: number;
  avg_difficulty: number;
  top_keywords: string[];
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
    // 🔥 新增：印出 Log 確認函式有被呼叫
    console.log(`[aiApi] 正在抓取課程 ${courseId} 的聚類資料...`); 
    
    try {
      const response = await apiClient.get<APIResponse<ClusterSummary[]>>(
        `/ai/clusters/${courseId}`
      );
      
      // 🔥 新增：印出後端回傳的資料結構，方便確認
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
      // 將參數帶入 API 請求
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
  updateCluster: async (clusterId: string, data: { topic_label?: string; is_locked?: boolean }) => {
    try {
      const response = await apiClient.patch(`/ai/clusters/${clusterId}`, data);
      return response.data;
    } catch (error) {
      console.error("Failed to update cluster:", error);
      return null;
    }
  }
};