"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import {
  Settings,
  MessageCircle,
  Send,
  Check,
  AlertCircle,
  Copy,
  CheckCircle2,
} from "lucide-react";
import {
  getLineConfig,
  getWebhookUrl,
  getLineStats,
  testLineConnection,
  getLineMessages,
  getMessageStats,
  getLineUsers,
  type LineMessage as ApiLineMessage,
  type LineUser,
} from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Spinner } from "@/components/ui/spinner";

interface LineMessage {
  id: string;
  sender: string;
  content: string;
  timestamp: string;
  status: "sent" | "received" | "failed";
}

interface DailyMessageStat {
  date: string;
  received: number;
  sent: number;
  failed: number;
}

interface DailyActivityStat {
  day: string;
  messages: number;
  users: number;
}

interface LineBot {
  channelId: string;
  channelName: string;
  isConnected: boolean;
  messagesCount: number;
  usersCount: number;
  followersCount: number;
  lastSync: string;
}

export default function LineIntegrationPage() {
  const [messages, setMessages] = useState<LineMessage[]>([]);
  const [users, setUsers] = useState<LineUser[]>([]);
  const [selectedUser, setSelectedUser] = useState<LineUser | null>(null);
  const [bot, setBot] = useState<LineBot>({
    channelId: "",
    channelName: "",
    isConnected: false,
    messagesCount: 0,
    usersCount: 0,
    followersCount: 0,
    lastSync: "",
  });
  const [newMessage, setNewMessage] = useState("");
  const [channelToken, setChannelToken] = useState("");
  const [showTokenForm, setShowTokenForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isConfigured, setIsConfigured] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [editedWebhookUrl, setEditedWebhookUrl] = useState("");
  const [isEditingWebhook, setIsEditingWebhook] = useState(false);
  const [webhookInstructions, setWebhookInstructions] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [messageStats, setMessageStats] = useState<DailyMessageStat[]>([]);
  const [dailyStats, setDailyStats] = useState<DailyActivityStat[]>([]);
  const { toast } = useToast();

  // 載入 LINE Bot 配置和狀態
  useEffect(() => {
    loadLineConfig();
    loadWebhookInfo();
    loadStats();
    loadUsers();
    loadMessageStats();
  }, []);

  // 當選中使用者改變時，載入該使用者的訊息
  useEffect(() => {
    if (selectedUser) {
      loadMessages(selectedUser.user_id);
    } else {
      loadMessages();
    }
  }, [selectedUser]);

  const loadLineConfig = async () => {
    try {
      setLoading(true);
      const config = await getLineConfig();
      setIsConfigured(config.is_configured);

      // 如果有 Bot 資訊，更新 Bot 狀態
      if (config.bot_info) {
        setBot((prev) => ({
          channelId: config.bot_info!.user_id,
          channelName: config.bot_info!.display_name,
          isConnected: config.is_configured,
          messagesCount: prev.messagesCount,
          usersCount: prev.usersCount,
          followersCount: config.followers_count || prev.followersCount,
          lastSync: new Date().toLocaleString("zh-TW", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          }),
        }));
      } else {
        setBot((prev) => ({
          ...prev,
          isConnected: config.is_configured,
          followersCount: config.followers_count || prev.followersCount,
        }));
      }
    } catch (error) {
      console.error("載入 LINE 配置失敗:", error);
      toast({
        title: "錯誤",
        description: "無法載入 LINE Bot 配置",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadWebhookInfo = async () => {
    try {
      const info = await getWebhookUrl();
      setWebhookUrl(info.webhook_url);
      setEditedWebhookUrl(info.webhook_url);
      setWebhookInstructions(info.instructions);

      // 如果不是 HTTPS，顯示警告
      if (!info.is_https) {
        toast({
          title: "提示",
          description:
            "LINE Webhook 需要 HTTPS URL，請使用 ngrok 或其他隧道服務",
          variant: "default",
        });
      }
    } catch (error) {
      console.error("載入 Webhook 資訊失敗:", error);
    }
  };

  const handleSaveWebhook = () => {
    setWebhookUrl(editedWebhookUrl);
    setIsEditingWebhook(false);
    toast({
      title: "已更新",
      description: "Webhook URL 已更新",
    });
  };

  const handleCancelEditWebhook = () => {
    setEditedWebhookUrl(webhookUrl);
    setIsEditingWebhook(false);
  };

  const loadStats = async () => {
    try {
      const data = await getLineStats();
      setStats(data);
      setBot((prev) => ({
        ...prev,
        messagesCount: data.messages_count,
        usersCount: data.users_count,
      }));
    } catch (error) {
      console.error("載入統計資料失敗:", error);
    }
  };

  const loadUsers = async () => {
    try {
      const data = await getLineUsers();
      setUsers(data.users);
    } catch (error) {
      console.error("載入使用者列表失敗:", error);
    }
  };

  const loadMessages = async (userId?: string) => {
    try {
      const data = await getLineMessages(50, 0, undefined, userId);
      // 轉換 API 訊息格式為前端格式
      const convertedMessages: LineMessage[] = data.messages.map((msg) => ({
        id: msg._id,
        sender: msg.direction === "received" ? msg.pseudonym : "系統",
        content: msg.content,
        timestamp: new Date(msg.created_at).toLocaleString("zh-TW", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        }),
        status: msg.direction,
      }));
      setMessages(convertedMessages);
    } catch (error) {
      console.error("載入訊息失敗:", error);
    }
  };

  const loadMessageStats = async () => {
    try {
      const data = await getMessageStats(7);

      // 轉換訊息統計資料
      const formattedMessageStats = data.daily_message_stats.map((stat) => {
        const date = new Date(stat.date);
        return {
          date: `${date.getMonth() + 1}月${date.getDate()}日`,
          received: stat.received,
          sent: stat.sent,
          failed: stat.failed,
        };
      });
      setMessageStats(formattedMessageStats);

      // 轉換每日活動統計
      const dates = Object.keys(data.daily_user_stats).sort();
      const weekDays = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"];
      const formattedDailyStats = dates.map((dateStr) => {
        const date = new Date(dateStr);
        const dayOfWeek = weekDays[date.getDay()];
        const messageCount =
          formattedMessageStats.find(
            (s) => s.date === `${date.getMonth() + 1}月${date.getDate()}日`
          )?.received || 0;
        return {
          day: dayOfWeek,
          messages:
            messageCount +
            (formattedMessageStats.find(
              (s) => s.date === `${date.getMonth() + 1}月${date.getDate()}日`
            )?.sent || 0),
          users: data.daily_user_stats[dateStr] || 0,
        };
      });
      setDailyStats(formattedDailyStats);
    } catch (error) {
      console.error("載入訊息統計失敗:", error);
      // 如果沒有資料，設定空陣列
      setMessageStats([]);
      setDailyStats([]);
    }
  };

  const handleTestConnection = async () => {
    try {
      const result = await testLineConnection();
      toast({
        title: result.success ? "成功" : "失敗",
        description: result.message,
        variant: result.success ? "default" : "destructive",
      });
      if (result.success) {
        loadLineConfig();
      }
    } catch (error) {
      toast({
        title: "錯誤",
        description: "測試連接失敗",
        variant: "destructive",
      });
    }
  };

  const copyWebhookUrl = () => {
    navigator.clipboard.writeText(editedWebhookUrl);
    setCopied(true);
    toast({
      title: "已複製",
      description: "Webhook URL 已複製到剪貼簿",
    });
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSendMessage = () => {
    if (newMessage.trim()) {
      const message: LineMessage = {
        id: String(messages.length + 1),
        sender: "系統",
        content: newMessage,
        timestamp: new Date().toLocaleString(),
        status: "sent",
      };
      setMessages([...messages, message]);
      setNewMessage("");
    }
  };

  const handleConnect = () => {
    if (channelToken) {
      setBot({ ...bot, isConnected: true });
      setShowTokenForm(false);
      setChannelToken("");
      alert("Line Bot 已成功連接");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <Spinner className="w-8 h-8 mx-auto mb-4" />
          <p className="text-muted-foreground">載入 LINE Bot 配置中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold text-foreground mb-2">Line 整合</h1>
          <p className="text-muted-foreground">管理 Line 機器人和訊息</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleTestConnection}
            variant="outline"
            className="gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            測試連接
          </Button>
          <Button
            onClick={() => setShowTokenForm(!showTokenForm)}
            variant={bot.isConnected ? "outline" : "default"}
            className="gap-2"
          >
            <Settings className="w-4 h-4" />
            {bot.isConnected ? "查看配置" : "查看配置"}
          </Button>
        </div>
      </div>

      {/* Configuration Info */}
      {showTokenForm && (
        <Card className="bg-secondary/50 border-primary/20 mb-6">
          <CardHeader>
            <CardTitle>LINE Bot 配置資訊</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">配置狀態</label>
              <div className="flex items-center gap-2 p-3 bg-background rounded-lg">
                {isConfigured ? (
                  <>
                    <Check className="w-5 h-5 text-green-600" />
                    <span className="text-green-600">已配置</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-5 h-5 text-yellow-600" />
                    <span className="text-yellow-600">未配置</span>
                  </>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                請在後端 .env 檔案中設定 LINE_CHANNEL_SECRET 和
                LINE_CHANNEL_ACCESS_TOKEN
              </p>
            </div>

            {webhookUrl && (
              <div>
                <label className="block text-sm font-medium mb-2">
                  Webhook URL
                  {editedWebhookUrl.startsWith("https://") ? (
                    <span className="ml-2 text-xs text-green-600">✓ HTTPS</span>
                  ) : (
                    <span className="ml-2 text-xs text-yellow-600">
                      ⚠ HTTP only
                    </span>
                  )}
                </label>
                <div className="flex gap-2">
                  <Input
                    value={editedWebhookUrl}
                    onChange={(e) => {
                      setEditedWebhookUrl(e.target.value);
                      setIsEditingWebhook(true);
                    }}
                    className={`font-mono text-sm ${
                      editedWebhookUrl.startsWith("https://")
                        ? "border-green-500/30"
                        : "border-yellow-500/30"
                    }`}
                    placeholder="輸入 Webhook URL"
                  />
                  {!isEditingWebhook ? (
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={copyWebhookUrl}
                    >
                      {copied ? (
                        <CheckCircle2 className="w-4 h-4 text-green-600" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  ) : (
                    <>
                      <Button
                        variant="default"
                        size="icon"
                        onClick={handleSaveWebhook}
                        title="儲存"
                      >
                        <Check className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={handleCancelEditWebhook}
                        title="取消"
                      >
                        <AlertCircle className="w-4 h-4" />
                      </Button>
                    </>
                  )}
                </div>
                {webhookUrl.includes("ngrok") && (
                  <p className="text-xs text-muted-foreground mt-2">
                    💡 使用 ngrok 隧道服務 •{" "}
                    <a
                      href="http://localhost:4040"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      查看控制台
                    </a>
                  </p>
                )}
              </div>
            )}

            {webhookInstructions.length > 0 && (
              <div>
                <label className="block text-sm font-medium mb-2">
                  設定步驟
                </label>
                <div className="bg-background p-4 rounded-lg space-y-2">
                  {webhookInstructions.map((instruction, index) => (
                    <p key={index} className="text-sm text-muted-foreground">
                      {instruction}
                    </p>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setShowTokenForm(false)}
                className="flex-1"
              >
                關閉
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connection Status */}
      <Card
        className={`mb-8 ${
          bot.isConnected
            ? "border-green-500/30 bg-green-50/50"
            : "border-destructive/30 bg-destructive/5"
        }`}
      >
        <CardContent className="pt-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              {bot.isConnected ? (
                <Check className="w-6 h-6 text-green-600" />
              ) : (
                <AlertCircle className="w-6 h-6 text-destructive" />
              )}
              <div>
                <p className="font-semibold">{bot.channelName}</p>
                <p className="text-sm text-muted-foreground">
                  {bot.isConnected
                    ? `已連接 • 最後同步: ${bot.lastSync}`
                    : "未連接"}
                </p>
              </div>
            </div>
            {bot.isConnected && (
              <div className="flex gap-6">
                <div className="text-right">
                  <p className="text-2xl font-bold text-green-600">
                    {bot.followersCount}
                  </p>
                  <p className="text-xs text-muted-foreground">好友人數</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-primary">
                    {bot.messagesCount}
                  </p>
                  <p className="text-xs text-muted-foreground">訊息總數</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-accent">
                    {bot.usersCount}
                  </p>
                  <p className="text-xs text-muted-foreground">活躍用戶</p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {bot.isConnected && (
        <>
          {/* Message Statistics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <Card>
              <CardHeader>
                <CardTitle>訊息趨勢</CardTitle>
              </CardHeader>
              <CardContent>
                {messageStats.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={messageStats}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="received" fill="#0066cc" name="收到" />
                      <Bar dataKey="sent" fill="#0052a3" name="發送" />
                      <Bar dataKey="failed" fill="#dc2626" name="失敗" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    <div className="text-center">
                      <p>尚無訊息資料</p>
                      <p className="text-sm mt-2">
                        透過 LINE Bot 收發訊息後將顯示統計資料
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>每日活動</CardTitle>
              </CardHeader>
              <CardContent>
                {dailyStats.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={dailyStats}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="messages"
                        stroke="#0066cc"
                        strokeWidth={2}
                        name="訊息"
                      />
                      <Line
                        type="monotone"
                        dataKey="users"
                        stroke="#0052a3"
                        strokeWidth={2}
                        name="用戶"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    <div className="text-center">
                      <p>尚無活動資料</p>
                      <p className="text-sm mt-2">
                        透過 LINE Bot 收發訊息後將顯示活動統計
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Message Console with User List */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageCircle className="w-5 h-5" />
                訊息控制台
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-12 gap-4 h-[600px]">
                {/* User List Sidebar */}
                <div className="col-span-4 border-r pr-4 overflow-y-auto">
                  <div className="mb-4">
                    <h3 className="font-semibold mb-2 flex items-center justify-between">
                      <span>使用者列表</span>
                      <span className="text-xs text-muted-foreground">
                        {users.length} 位使用者
                      </span>
                    </h3>
                    <Button
                      variant={!selectedUser ? "default" : "outline"}
                      size="sm"
                      className="w-full justify-start mb-2"
                      onClick={() => setSelectedUser(null)}
                    >
                      <MessageCircle className="w-4 h-4 mr-2" />
                      所有訊息
                    </Button>
                  </div>
                  <div className="space-y-2">
                    {users.length > 0 ? (
                      users.map((user) => (
                        <div
                          key={user.user_id}
                          onClick={() => setSelectedUser(user)}
                          className={`p-3 rounded-lg cursor-pointer transition-colors ${
                            selectedUser?.user_id === user.user_id
                              ? "bg-primary text-primary-foreground"
                              : "bg-secondary/50 hover:bg-secondary"
                          }`}
                        >
                          <div className="flex items-start justify-between mb-1">
                            <p className="font-medium text-sm truncate">
                              {user.pseudonym}
                            </p>
                            <span className="text-xs opacity-70 ml-2 whitespace-nowrap">
                              {user.message_count}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-xs opacity-70">
                            <span>
                              收 {user.received_count} / 發 {user.sent_count}
                            </span>
                            {user.last_message_time && (
                              <span className="text-xs">
                                {new Date(
                                  user.last_message_time
                                ).toLocaleDateString("zh-TW", {
                                  month: "2-digit",
                                  day: "2-digit",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </span>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <p className="text-sm">尚無使用者</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Chat Area */}
                <div className="col-span-8 flex flex-col">
                  {/* Chat Header */}
                  <div className="mb-4 pb-3 border-b">
                    <h3 className="font-semibold">
                      {selectedUser
                        ? `與 ${selectedUser.pseudonym} 的對話`
                        : "所有訊息"}
                    </h3>
                    {selectedUser && (
                      <p className="text-xs text-muted-foreground mt-1">
                        共 {selectedUser.message_count} 則訊息
                      </p>
                    )}
                  </div>

                  {/* Messages */}
                  <div className="flex-1 space-y-3 bg-secondary/30 rounded-lg p-4 overflow-y-auto mb-4">
                    {messages.length > 0 ? (
                      messages.map((msg) => (
                        <div
                          key={msg.id}
                          className={`flex ${
                            msg.status === "sent"
                              ? "justify-end"
                              : "justify-start"
                          }`}
                        >
                          <div
                            className={`max-w-[70%] px-4 py-2 rounded-lg ${
                              msg.status === "sent"
                                ? "bg-primary text-primary-foreground"
                                : msg.status === "received"
                                ? "bg-background text-foreground border"
                                : "bg-destructive/10 text-destructive"
                            }`}
                          >
                            <p className="text-xs font-medium mb-1">
                              {msg.sender}
                            </p>
                            <p className="text-sm break-words">{msg.content}</p>
                            <p className="text-xs opacity-70 mt-1">
                              {msg.timestamp}
                            </p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-12 text-muted-foreground">
                        <MessageCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>尚無訊息記錄</p>
                        {!selectedUser && (
                          <p className="text-sm mt-2">
                            選擇使用者或開始透過 LINE Bot 與學生互動吧！
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Message Input */}
                  <div className="flex gap-2">
                    <Input
                      placeholder={
                        selectedUser
                          ? `發送訊息給 ${selectedUser.pseudonym}...`
                          : "請先選擇使用者..."
                      }
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyPress={(e) =>
                        e.key === "Enter" && handleSendMessage()
                      }
                      disabled={!selectedUser}
                    />
                    <Button
                      onClick={handleSendMessage}
                      className="gap-2"
                      disabled={!newMessage.trim() || !selectedUser}
                    >
                      <Send className="w-4 h-4" />
                      發送
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {!bot.isConnected && (
        <Card className="bg-secondary/30 border-dashed">
          <CardContent className="pt-12 pb-12 text-center">
            <MessageCircle className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-muted-foreground mb-4">Line Bot 尚未連接</p>
            <p className="text-sm text-muted-foreground">
              點擊上方按鈕連接您的 Line Bot 以開始整合
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
