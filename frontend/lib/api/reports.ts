/**
 * 報表與統計 API
 */

import { apiClient, ApiResponse } from "../api-client";
// 1. 🔥 修改：從 ai.ts 匯入 ClusterSummary，避免重複定義
import { ClusterSummary } from "./ai";

/**
 * 統計資料介面
 */
export interface Statistics {
  total_questions: number;
  pending_questions: number;
  approved_questions: number;
  rejected_questions: number;
  deleted_questions: number;
  withdrawn_questions: number;
  avg_difficulty_score: number;
  status_distribution: {
    [key: string]: number;
  };
  difficulty_distribution: {
    [key: string]: number;
  };
  cluster_count: number;
}

// 2. 🔥 修改：刪除這裡原本的 export interface ClusterSummary { ... }
// 因為已經改從上方 import 了

/**
 * 報表 API
 */
export const reportsApi = {
  /**
   * 取得統計資料
   */
  async getStatistics(params: {
    course_id: string;
    class_id?: string;
  }): Promise<ApiResponse<Statistics>> {
    const response = await apiClient.get<Statistics>(
      "/questions/statistics/",
      params
    );
    return response;
  },

  /**
   * 取得聚類摘要
   */
  async getClustersSummary(
    courseId: string
  ): Promise<ApiResponse<ClusterSummary[]>> {
    const response = await apiClient.get<ClusterSummary[]>(
      `/ai/clusters/${courseId}`
    );
    return response;
  },

  /**
   * 匯出提問 CSV
   */
  async exportQuestions(params: {
    course_id: string;
    class_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<Blob> {
    const queryString = new URLSearchParams(
      Object.entries(params).filter(([_, v]) => v !== undefined) as [
        string,
        string
      ][]
    ).toString();
    const API_BASE_URL =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(
      `${API_BASE_URL}/reports/export/questions?${queryString}`
    );
    if (!response.ok) {
      throw new Error(`匯出失敗: ${response.status}`);
    }
    return await response.blob();
  },

  /**
   * 匯出 Q&A CSV
   */
  async exportQAs(params: {
    course_id: string;
    class_id?: string;
  }): Promise<Blob> {
    const queryString = new URLSearchParams(
      Object.entries(params).filter(([_, v]) => v !== undefined) as [
        string,
        string
      ][]
    ).toString();
    const API_BASE_URL =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(
      `${API_BASE_URL}/reports/export/qas?${queryString}`
    );
    if (!response.ok) {
      throw new Error(`匯出失敗: ${response.status}`);
    }
    return await response.blob();
  },

  /**
   * 匯出統計資料 CSV
   */
  async exportStatistics(params: {
    course_id: string;
    class_id?: string;
  }): Promise<Blob> {
    const queryString = new URLSearchParams(
      Object.entries(params).filter(([_, v]) => v !== undefined) as [
        string,
        string
      ][]
    ).toString();
    const API_BASE_URL =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(
      `${API_BASE_URL}/reports/export/statistics?${queryString}`
    );
    if (!response.ok) {
      throw new Error(`匯出失敗: ${response.status}`);
    }
    return await response.blob();
  },

  // 3. 🔥 新增：匯出 AI 主題分析報表
  async exportClusters(params: { course_id: string }): Promise<Blob> {
    const queryString = new URLSearchParams(
      Object.entries(params).filter(([_, v]) => v !== undefined) as [
        string,
        string
      ][]
    ).toString();
    const API_BASE_URL =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(
      `${API_BASE_URL}/reports/export/clusters?${queryString}`
    );
    if (!response.ok) {
      throw new Error(`匯出失敗: ${response.status}`);
    }
    return await response.blob();
  },
};