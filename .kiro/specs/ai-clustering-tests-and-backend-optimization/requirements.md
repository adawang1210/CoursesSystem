# Requirements Document

## Introduction

本功能涵蓋兩大工作項目：(1) 驗證 AI 聚類分析流程並撰寫完整的整合測試案例，確保從取得已審核回答、建構 Gemini API 提示詞、解析回應到寫入資料庫的完整管線正確運作；(2) 全面優化 backend/app/ 的程式碼品質，包含效能優化（消除 N+1 查詢、新增資料庫索引）、錯誤處理強化、程式碼品質提升、安全性加固，以及 AI Service 的重試邏輯與逾時處理。

## Glossary

- **Clustering_Pipeline**: AI 聚類分析管線，從取得學生回答到呼叫 Gemini API 進行分群並寫入資料庫的完整流程
- **AI_Service**: 位於 `backend/app/services/ai_service.py` 的 AI 服務模組，負責與 Google Gemini API 互動
- **Question_Service**: 位於 `backend/app/services/question_service.py` 的作答紀錄管理服務
- **Course_Service**: 位於 `backend/app/services/course_service.py` 的課程管理服務
- **Export_Service**: 位於 `backend/app/services/export_service.py` 的資料匯出服務
- **API_Endpoint**: FastAPI 路由端點，處理 HTTP 請求與回應
- **Gemini_API**: Google Gemini 生成式 AI API，用於聚類分析與回覆草稿生成
- **Motor_Driver**: MongoDB 的 Python 非同步驅動程式
- **Cluster_Document**: 儲存於 MongoDB `clusters` 集合中的聚類主題文件
- **Question_Document**: 儲存於 MongoDB `questions` 集合中的學生作答紀錄文件
- **N_Plus_One_Query**: 一種效能反模式，在迴圈中逐筆查詢資料庫而非使用批次查詢
- **ObjectId**: MongoDB 的文件唯一識別碼格式

## Requirements

### Requirement 1: AI 聚類管線整合測試 — 取得已審核回答

**User Story:** 身為開發者，我希望驗證 Clustering_Pipeline 能正確從資料庫取得已審核（approved）且尚未分類的學生回答，以確保聚類分析的輸入資料正確。

#### Acceptance Criteria

1. WHEN `get_replies_for_clustering` is called with a valid qa_id, THE Question_Service SHALL return only Question_Document records with `review_status` equal to "approved" and `cluster_id` equal to None
2. WHEN `get_replies_for_clustering` is called with a valid qa_id, THE Question_Service SHALL return each reply containing `_id`, `pseudonym`, `answer_text`, and `created_at` fields
3. WHEN no approved unclustered answers exist for the given qa_id, THE Question_Service SHALL return an empty list
4. WHEN `get_replies_for_clustering` is called with a limit parameter, THE Question_Service SHALL return at most the specified number of replies

### Requirement 2: AI 聚類管線整合測試 — 建構聚類提示詞

**User Story:** 身為開發者，我希望驗證 AI_Service 能正確建構包含教師問題、核心觀念、預期迷思與學生回答的提示詞，以確保 Gemini_API 收到完整的分析資訊。

#### Acceptance Criteria

1. WHEN `perform_qa_answer_clustering` is called, THE AI_Service SHALL construct a prompt containing the `teacher_question`, `core_concept`, and `expected_misconceptions` parameters
2. WHEN `perform_qa_answer_clustering` is called with student answers, THE AI_Service SHALL include each student answer in the prompt with a sequential index prefix (ID_0, ID_1, ...)
3. WHEN `perform_qa_answer_clustering` is called with `existing_topics`, THE AI_Service SHALL include the existing topic labels in the prompt to guide cluster reuse
4. WHEN `perform_qa_answer_clustering` is called with an empty student_answers list, THE AI_Service SHALL return `{"clusters": []}` without calling Gemini_API

### Requirement 3: AI 聚類管線整合測試 — Gemini API 呼叫驗證

**User Story:** 身為開發者，我希望驗證 AI_Service 對 Gemini_API 的呼叫格式正確（模型名稱、API 金鑰、請求格式），以確保 API 整合的穩定性。

#### Acceptance Criteria

1. WHEN `_call_gemini` is invoked, THE AI_Service SHALL use the model name specified in `settings.GEMINI_MODEL`
2. WHEN `_call_gemini` is invoked with `json_mode=True`, THE AI_Service SHALL set `response_mime_type` to "application/json" in the request configuration
3. IF the `GEMINI_API_KEY` setting is empty, THEN THE AI_Service SHALL raise a ValueError with a descriptive error message
4. IF the Gemini_API returns an invalid JSON response in json_mode, THEN THE AI_Service SHALL return an empty dictionary

### Requirement 4: AI 聚類管線整合測試 — 回應解析與資料庫寫入

**User Story:** 身為開發者，我希望驗證 Clustering_Pipeline 能正確解析 Gemini_API 回應並將聚類結果寫入資料庫，以確保端到端流程的完整性。

#### Acceptance Criteria

1. WHEN the Gemini_API returns a valid clustering response, THE Clustering_Pipeline SHALL create Cluster_Document records in the `clusters` collection with `topic_label`, `summary`, `course_id`, and `qa_id` fields
2. WHEN the Gemini_API returns a valid clustering response, THE Clustering_Pipeline SHALL update each Question_Document with the assigned `cluster_id`
3. WHEN the Gemini_API returns a response with `question_indices` referencing valid student answers, THE Clustering_Pipeline SHALL map each index to the correct Question_Document `_id`
4. IF the Gemini_API returns a response missing the `clusters` key, THEN THE Clustering_Pipeline SHALL raise a ValueError with message "AI 回傳格式錯誤"

### Requirement 5: AI 聚類管線整合測試 — 錯誤情境處理

**User Story:** 身為開發者，我希望驗證 Clustering_Pipeline 在異常情境下能優雅地處理錯誤，以確保系統的穩健性。

#### Acceptance Criteria

1. WHEN no approved answers exist for the target qa_id, THE API_Endpoint SHALL return a success response with message "沒有新的未分類回答，工作結束"
2. IF the Gemini_API returns HTTP 401 or 403 due to an invalid API key, THEN THE AI_Service SHALL return None from `_call_gemini` and log the error
3. IF the Gemini_API call raises an unexpected exception, THEN THE API_Endpoint SHALL return HTTP 500 with a `detail` field describing the failure

### Requirement 6: 效能優化 — 消除 N+1 查詢模式

**User Story:** 身為開發者，我希望消除 Course_Service 和 Export_Service 中的 N+1 查詢模式，以減少資料庫往返次數並提升 API 回應速度。

#### Acceptance Criteria

1. WHEN `get_courses` is called, THE Course_Service SHALL use MongoDB aggregation pipeline or bulk queries to fetch question counts and student counts for all courses in a single operation, instead of querying per course in a loop
2. WHEN `export_qas_to_csv` is called, THE Export_Service SHALL use a single bulk query to fetch all replies for all QA tasks, instead of querying per QA in a loop
3. WHEN `batch_update_review_status` is called, THE API_Endpoint SHALL use a single `update_many` operation to update all Question_Document records, instead of calling `update_review_status` per question in a loop

### Requirement 7: 效能優化 — 資料庫索引建立

**User Story:** 身為開發者，我希望為常用查詢欄位建立資料庫索引，以加速查詢效能。

#### Acceptance Criteria

1. WHEN the application starts, THE Database module SHALL create indexes on the `questions` collection for fields: `course_id`, `reply_to_qa_id`, `cluster_id`, `review_status`, and the compound index `{reply_to_qa_id: 1, pseudonym: 1}`
2. WHEN the application starts, THE Database module SHALL create indexes on the `clusters` collection for fields: `course_id`, `qa_id`, and the compound index `{course_id: 1, qa_id: 1}`
3. WHEN the application starts, THE Database module SHALL create indexes on the `qas` collection for fields: `course_id` and `{course_id: 1, allow_replies: 1, expires_at: 1}`
4. WHEN the application starts, THE Database module SHALL create an index on the `line_users` collection for field `current_course_id`

### Requirement 8: 錯誤處理優化

**User Story:** 身為開發者，我希望強化整個後端的錯誤處理機制，以提供一致的錯誤回應格式並避免錯誤被靜默吞噬。

#### Acceptance Criteria

1. THE API_Endpoint layer SHALL return all error responses in the format `{"detail": "error message"}` using FastAPI HTTPException
2. WHEN an ObjectId parameter is received by any API_Endpoint, THE API_Endpoint SHALL validate the ObjectId format using `bson.ObjectId.is_valid()` before executing database queries, and return HTTP 400 if invalid
3. WHEN a bare `except Exception` block catches an error, THE handler SHALL log the error with `traceback` information before re-raising or returning an error response
4. IF an error occurs during database operations in service layer functions, THEN THE service SHALL raise a specific exception type (ValueError, RuntimeError) instead of returning None silently

### Requirement 9: 程式碼品質優化

**User Story:** 身為開發者，我希望提升程式碼品質，移除無用程式碼、消除重複邏輯，並確保所有非同步操作正確使用 `await`。

#### Acceptance Criteria

1. THE codebase SHALL contain no unused imports across all Python files in `backend/app/`
2. THE codebase SHALL extract shared date-range query building logic into a reusable utility function in `datetime_helper.py`
3. THE AI_Service SHALL convert `perform_qa_answer_clustering` and `_call_gemini` to async functions using `asyncio` to avoid blocking the event loop when called from async context
4. THE codebase SHALL replace all hardcoded values (such as batch sizes, default limits) with named constants or configuration variables

### Requirement 10: 安全性優化

**User Story:** 身為開發者，我希望加固後端的安全性，確保使用者輸入經過驗證、CORS 設定適當，以防止常見的安全漏洞。

#### Acceptance Criteria

1. WHEN any API_Endpoint receives an `id` parameter intended as a MongoDB ObjectId, THE API_Endpoint SHALL wrap the ObjectId parsing in a try/except block and return HTTP 400 with a descriptive message for malformed IDs
2. THE CORS middleware SHALL use explicit allowed methods list `["GET", "POST", "PATCH", "DELETE", "OPTIONS"]` instead of wildcard `["*"]`
3. THE CORS middleware SHALL use explicit allowed headers list instead of wildcard `["*"]`

### Requirement 11: AI Service 重試與逾時機制

**User Story:** 身為開發者，我希望 AI_Service 具備 Gemini_API 呼叫的重試邏輯與逾時處理，以應對暫時性網路故障與 API 限流。

#### Acceptance Criteria

1. WHEN the Gemini_API returns HTTP 429 (Too Many Requests) or HTTP 503 (Service Unavailable), THE AI_Service SHALL retry the request up to 3 times with exponential backoff (1s, 2s, 4s delays)
2. WHEN the Gemini_API call exceeds 30 seconds without response, THE AI_Service SHALL abort the request and raise a TimeoutError
3. IF all retry attempts fail, THEN THE AI_Service SHALL log the final error and return None
4. WHEN a retry is triggered, THE AI_Service SHALL log the retry attempt number and the error that caused the retry

### Requirement 12: AI 聚類提示詞優化

**User Story:** 身為開發者，我希望優化聚類分析的提示詞，使其更適合台灣大學生關於電子商務主題的回答分析，以提升聚類品質。

#### Acceptance Criteria

1. THE AI_Service SHALL include Traditional Chinese (繁體中文) instructions in the clustering prompt specifying that all output labels and summaries must be in Traditional Chinese
2. THE AI_Service SHALL include domain-specific guidance in the prompt for analyzing e-commerce related student answers, referencing common Taiwan e-commerce platforms and concepts
3. WHEN `max_clusters` is specified, THE AI_Service SHALL instruct the Gemini_API to produce at most the specified number of clusters in the prompt
4. THE AI_Service SHALL truncate individual student answers to a maximum of 300 characters in the prompt to prevent token overflow
