/**
 * 提問相關 API
 */

import { apiClient } from "../api-client";

export interface Question {
  _id?: string;
  course_id: string;
  class_id?: string;
  pseudonym: string;
  question_text: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "DELETED" | "WITHDRAWN";
  cluster_id?: string;
  ai_analysis?: {
    difficulty_score?: number;
    difficulty_level?: "EASY" | "MEDIUM" | "HARD" | "VERY_HARD";
    keywords?: string[];
    analyzed_at?: string;
  };
  merged_to_qa_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateQuestionDto {
  course_id: string;
  class_id?: string;
  line_user_id: string;
  question_text: string;
}

export interface UpdateQuestionStatusDto {
  status: "APPROVED" | "REJECTED" | "DELETED" | "WITHDRAWN";
  rejection_reason?: string;
}

export interface MergeQuestionsDto {
  question_ids: string[];
  merged_question: string;
  answer: string;
  category?: string;
  tags?: string[];
}

export const questionsApi = {
  // 獲取所有提問
  async getAll(params?: {
    course_id?: string;
    status?: string;
    cluster_id?: string;
    skip?: number;
    limit?: number;
  }) {
    const response = await apiClient.get<Question[]>("/questions/", params);
    return response.data || [];
  },

  // 獲取單一提問
  async getById(id: string) {
    const response = await apiClient.get<Question>(`/questions/${id}`);
    return response.data;
  },

  // 創建提問
  async create(data: CreateQuestionDto) {
    const response = await apiClient.post<Question>("/questions/", data);
    return response.data;
  },

  // 更新提問狀態
  async updateStatus(id: string, data: UpdateQuestionStatusDto) {
    const response = await apiClient.patch<Question>(
      `/questions/${id}/status`,
      data
    );
    return response.data;
  },

  // 合併提問到 Q&A
  async merge(data: MergeQuestionsDto) {
    const response = await apiClient.post("/questions/merge", data);
    return response.data;
  },

  // 獲取統計資料
  async getStatistics(courseId?: string) {
    const params = courseId ? { course_id: courseId } : undefined;
    const response = await apiClient.get("/questions/statistics/", params);
    return response.data;
  },

  // 刪除提問
  async delete(id: string) {
    return apiClient.delete(`/questions/${id}`);
  },
};
