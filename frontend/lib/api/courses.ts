/**
 * 課程相關 API
 */

import { apiClient } from "../api-client";

export interface Course {
  _id?: string;
  course_code: string;
  course_name: string;
  semester: string;
  instructor?: string;
  description?: string;
  is_active?: boolean;
  sync_source?: string;
  sync_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateCourseDto {
  course_code: string;
  course_name: string;
  semester: string;
  instructor?: string;
  description?: string;
  is_active?: boolean;
}

export interface UpdateCourseDto {
  course_name?: string;
  semester?: string;
  instructor?: string;
  description?: string;
  is_active?: boolean;
}

export const coursesApi = {
  // 獲取所有課程
  async getAll(params?: {
    skip?: number;
    limit?: number;
    is_active?: boolean;
  }) {
    const response = await apiClient.get<Course[]>("/courses/", params);
    return response.data || [];
  },

  // 獲取單一課程
  async getById(id: string) {
    const response = await apiClient.get<Course>(`/courses/${id}`);
    return response.data;
  },

  // 創建課程
  async create(data: CreateCourseDto) {
    const response = await apiClient.post<Course>("/courses/", data);
    return response.data;
  },

  // 更新課程
  async update(id: string, data: UpdateCourseDto) {
    const response = await apiClient.patch<Course>(`/courses/${id}`, data);
    return response.data;
  },

  // 刪除課程
  async delete(id: string) {
    return apiClient.delete(`/courses/${id}`);
  },
};
