/**
 * 學生作答回覆 相關 API
 * 註：系統已轉型為 Q&A 任務模式，此處的 Question 實體代表學生對課後任務的作答。
 */

import { apiClient } from "../api-client";

export interface Question {
  _id?: string;
  course_id: string;
  class_id?: string;
  pseudonym: string;
  question_text: string; // 學生的作答內容
  
  // =========== 🔥 新增：批閱狀態與評語 ===========
  review_status?: "pending" | "approved" | "rejected";
  feedback?: string;
  // ==============================================
  
  // AI 批閱與分析欄位
  cluster_id?: string;
  difficulty_score?: number;
  difficulty_level?: "easy" | "medium" | "hard" | "EASY" | "MEDIUM" | "HARD";
  keywords?: string[];
  ai_response_draft?: string;  // AI 生成的回覆草稿
  ai_summary?: string;         // AI 對問題的摘要
  sentiment_score?: number;    // 情緒分數
  
  // 來源與關聯
  source?: string;             // 來源 (例如: "LINE" 或 "WEB")
  original_message_id?: string;// LINE 原始訊息 ID
  reply_to_qa_id?: string;     // 標記此作答是屬於哪一個 Q&A 任務
  
  created_at?: string;
  updated_at?: string;
}

export interface CreateQuestionDto {
  course_id: string;
  class_id?: string;
  line_user_id: string;
  question_text: string;
  reply_to_qa_id?: string;
}

// 🔥 新增：更新單筆批閱狀態的資料格式
export interface UpdateReviewStatusDto {
  review_status: "pending" | "approved" | "rejected";
  feedback?: string;
}

// =========== 🔥 新增：批量更新狀態的資料格式 ===========
export interface BatchUpdateReviewStatusDto {
  question_ids: string[];
  review_status: "pending" | "approved" | "rejected";
  feedback?: string;
}
// ====================================================

export const questionsApi = {
  // 獲取所有學生作答
  async getAll(params?: {
    course_id?: string;
    cluster_id?: string;
    reply_to_qa_id?: string;
    skip?: number;
    limit?: number;
  }) {
    const response = await apiClient.get<Question[]>("/questions/", params);
    return response.data || [];
  },

  // 獲取單一作答紀錄
  async getById(id: string) {
    const response = await apiClient.get<Question>(`/questions/${id}`);
    return response.data;
  },

  // =========== 🔥 新增：獲取特定聚類底下的所有作答 ===========
  async getByCluster(cluster_id: string, course_id: string) {
    const response = await apiClient.get<any>(`/questions/cluster/${cluster_id}`, { course_id });
    // 依據專案 apiClient 的封裝，這裡可能直接是 data 陣列，或包在 data.data 裡
    return response.data?.data || response.data || [];
  },
  // ========================================================

  // 呼叫更新單筆批閱狀態的 API
  async updateReviewStatus(id: string, data: UpdateReviewStatusDto) {
    const response = await apiClient.patch<Question>(
      `/questions/${id}/review`,
      data
    );
    return response.data;
  },

  // 呼叫批量更新批閱狀態的 API
  async batchUpdateReviewStatus(data: BatchUpdateReviewStatusDto) {
    const response = await apiClient.post(
      `/questions/batch-review`,
      data
    );
    return response.data;
  },

  // 刪除作答紀錄
  async delete(id: string) {
    return apiClient.delete(`/questions/${id}`);
  },
};