/**
 * API 客戶端配置
 * 用於連接 FastAPI 後端
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiResponse<T> {
  success?: boolean;
  data?: T;
  detail?: string;
  message?: string;
  total?: number;
}

class ApiClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
      });

      if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
          const error = await response.json();
          // 處理 FastAPI 的驗證錯誤格式
          if (error.detail) {
            if (Array.isArray(error.detail)) {
              // Pydantic 驗證錯誤
              errorMessage = error.detail
                .map((err: any) => `${err.loc.join(".")}: ${err.msg}`)
                .join(", ");
            } else if (typeof error.detail === "string") {
              errorMessage = error.detail;
            } else {
              errorMessage = JSON.stringify(error.detail);
            }
          } else if (error.message) {
            errorMessage = error.message;
          }
        } catch (e) {
          // 如果無法解析 JSON，使用預設錯誤訊息
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("API request failed:", error);
      throw error;
    }
  }

  // GET 請求
  async get<T>(
    endpoint: string,
    params?: Record<string, any>
  ): Promise<ApiResponse<T>> {
    const queryString = params
      ? "?" + new URLSearchParams(params).toString()
      : "";
    return this.request<T>(`${endpoint}${queryString}`, {
      method: "GET",
    });
  }

  // POST 請求
  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // PATCH 請求
  async patch<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  // DELETE 請求
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "DELETE",
    });
  }
}

// 創建全域 API 客戶端實例
export const apiClient = new ApiClient(API_BASE_URL);

// 匯出 API 基礎 URL 供其他地方使用
export const API_URL = API_BASE_URL;
