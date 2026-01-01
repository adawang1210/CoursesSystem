/**
 * LINE Bot 整合 API
 */
import { apiClient } from "../api-client";

export interface LineConfig {
  is_configured: boolean;
  has_channel_secret: boolean;
  has_access_token: boolean;
  channel_secret_length: number;
  access_token_length: number;
  bot_info?: {
    display_name: string;
    user_id: string;
    picture_url?: string;
    status_message?: string;
  };
  followers_count?: number;
}

export interface WebhookInfo {
  webhook_url: string;
  is_https: boolean;
  instructions: string[];
}

export interface LineStats {
  messages_count: number;
  received_count: number;
  sent_count: number;
  failed_count: number;
  users_count: number;
  questions_from_line: number;
  last_message_time: string | null;
}

export interface LineMessage {
  _id: string;
  user_id: string;
  pseudonym: string;
  message_type: string;
  direction: "received" | "sent" | "failed";
  content: string;
  line_message_id?: string;
  reply_token?: string;
  error_message?: string;
  created_at: string;
}

export interface LineMessagesResponse {
  messages: LineMessage[];
  total: number;
  limit: number;
  offset: number;
}

export interface DailyMessageStat {
  date: string;
  received: number;
  sent: number;
  failed: number;
}

export interface MessageStatsResponse {
  daily_message_stats: DailyMessageStat[];
  daily_user_stats: Record<string, number>;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  data?: {
    channel_secret: string;
    access_token: string;
  };
}

export interface LineUser {
  user_id: string;
  pseudonym: string;
  message_count: number;
  received_count: number;
  sent_count: number;
  last_message_time: string | null;
}

export interface LineUsersResponse {
  users: LineUser[];
  total: number;
}

/**
 * 取得 LINE Bot 配置狀態
 */
export async function getLineConfig(): Promise<LineConfig> {
  const response = await apiClient.get<{ success: boolean; data: LineConfig }>(
    "/line/config"
  );
  return response.data;
}

/**
 * 取得 Webhook URL 和設定說明
 */
export async function getWebhookUrl(): Promise<WebhookInfo> {
  const response = await apiClient.get<{ success: boolean; data: WebhookInfo }>(
    "/line/webhook-url"
  );
  return response.data;
}

/**
 * 取得 LINE Bot 統計資訊
 */
export async function getLineStats(courseId?: string): Promise<LineStats> {
  const params = courseId ? { course_id: courseId } : {};
  const response = await apiClient.get<{ success: boolean; data: LineStats }>(
    "/line/stats",
    { params }
  );
  return response.data;
}

/**
 * 測試 LINE Bot 連接
 */
export async function testLineConnection(): Promise<TestConnectionResponse> {
  const response = await apiClient.post<TestConnectionResponse>(
    "/line/test-connection"
  );
  return response;
}

/**
 * 取得 LINE 使用者列表
 */
export async function getLineUsers(): Promise<LineUsersResponse> {
  const response = await apiClient.get<{
    success: boolean;
    data: LineUsersResponse;
  }>("/line/users");
  return response.data;
}

/**
 * 取得 LINE 訊息歷史
 */
export async function getLineMessages(
  limit: number = 50,
  offset: number = 0,
  direction?: "received" | "sent" | "failed",
  userId?: string
): Promise<LineMessagesResponse> {
  const params: any = { limit, offset };
  if (direction) params.direction = direction;
  if (userId) params.user_id = userId;

  const response = await apiClient.get<{
    success: boolean;
    data: LineMessagesResponse;
  }>("/line/messages", { params });
  return response.data;
}

/**
 * 取得訊息統計資料
 */
export async function getMessageStats(
  days: number = 7
): Promise<MessageStatsResponse> {
  const response = await apiClient.get<{
    success: boolean;
    data: MessageStatsResponse;
  }>("/line/message-stats", {
    params: { days },
  });
  return response.data;
}

/**
 * 發送訊息到 LINE
 */
export async function sendLineMessage(
  userId: string,
  message: string
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post<{
    success: boolean;
    message: string;
  }>("/line/send-message", {
    user_id: userId,
    message,
  });
  return response;
}
