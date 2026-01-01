/**
 * Q&A 相關 API
 */

import { apiClient } from "../api-client";

export interface QA {
  _id?: string;
  course_id: string;
  question: string;
  answer: string;
  category?: string;
  tags?: string[];
  related_question_ids?: string[];
  is_published?: boolean;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateQADto {
  course_id: string;
  question: string;
  answer: string;
  category?: string;
  tags?: string[];
  related_question_ids?: string[];
  is_published?: boolean;
  created_by?: string;
}

export interface UpdateQADto {
  question?: string;
  answer?: string;
  category?: string;
  tags?: string[];
  is_published?: boolean;
}

export const qasApi = {
  // 獲取所有 Q&A
  async getAll(params?: {
    course_id?: string;
    is_published?: boolean;
    skip?: number;
    limit?: number;
  }) {
    const response = await apiClient.get<QA[]>("/qas/", params);
    return response.data || [];
  },

  // 獲取單一 Q&A
  async getById(id: string) {
    const response = await apiClient.get<QA>(`/qas/${id}`);
    return response.data;
  },

  // 創建 Q&A
  async create(data: CreateQADto) {
    // 將 created_by 作為查詢參數，其餘作為請求體
    const { created_by = "admin", ...bodyData } = data;
    const params = new URLSearchParams({ created_by });
    const response = await apiClient.post<QA>(
      `/qas/?${params.toString()}`,
      bodyData
    );
    return response.data;
  },

  // 更新 Q&A
  async update(id: string, data: UpdateQADto) {
    const response = await apiClient.patch<QA>(`/qas/${id}`, data);
    return response.data;
  },

  // 刪除 Q&A
  async delete(id: string) {
    return apiClient.delete(`/qas/${id}`);
  },

  // 搜尋 Q&A
  async search(params: { course_id?: string; query: string }) {
    const response = await apiClient.get<QA[]>("/qas/search/", params);
    return response.data || [];
  },

  // 連結提問到 Q&A
  async linkQuestions(id: string, questionIds: string[]) {
    return apiClient.post(`/qas/${id}/link-questions`, {
      question_ids: questionIds,
    });
  },
};
