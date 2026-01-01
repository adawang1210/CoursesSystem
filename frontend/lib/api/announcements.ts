/**
 * 公告相關 API
 */

import { apiClient } from "../api-client";

export interface Announcement {
  _id?: string;
  course_id: string;
  title: string;
  content: string;
  is_published?: boolean;
  related_qa_ids?: string[];
  line_sent?: boolean;
  line_sent_at?: string;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateAnnouncementDto {
  course_id: string;
  title: string;
  content: string;
  is_published?: boolean;
  related_qa_ids?: string[];
}

export interface UpdateAnnouncementDto {
  title?: string;
  content?: string;
  is_published?: boolean;
  related_qa_ids?: string[];
}

export const announcementsApi = {
  // 獲取所有公告
  async getAll(params?: {
    course_id?: string;
    is_published?: boolean;
    skip?: number;
    limit?: number;
  }) {
    const response = await apiClient.get<Announcement[]>(
      "/announcements/",
      params
    );
    return response.data || [];
  },

  // 獲取單一公告
  async getById(id: string) {
    const response = await apiClient.get<Announcement>(`/announcements/${id}`);
    return response.data;
  },

  // 創建公告
  async create(data: CreateAnnouncementDto) {
    const response = await apiClient.post<Announcement>(
      "/announcements/",
      data
    );
    return response.data;
  },

  // 更新公告
  async update(id: string, data: UpdateAnnouncementDto) {
    const response = await apiClient.patch<Announcement>(
      `/announcements/${id}`,
      data
    );
    return response.data;
  },

  // 刪除公告
  async delete(id: string) {
    return apiClient.delete(`/announcements/${id}`);
  },

  // 發送公告到 Line
  async sendToLine(id: string) {
    const response = await apiClient.post(`/announcements/${id}/send-line`);
    return response.data;
  },
};
