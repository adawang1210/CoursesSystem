# Implementation Plan: AI Clustering Tests & Backend Optimization

## Overview

本計畫將依序實作：(1) 共用工具與設定更新、(2) AIService 非同步重構含重試/逾時、(3) N+1 查詢消除、(4) 資料庫索引管理、(5) CORS 安全性加固與 ObjectId 驗證、(6) 完整測試套件。每個步驟都建立在前一步的基礎上，最終整合驗證。

## Tasks

- [x] 1. 設定更新與共用工具建立
  - [x] 1.1 在 `backend/app/config.py` 新增 AI 重試/逾時設定欄位
    - 新增 `GEMINI_RETRY_MAX_ATTEMPTS: int = 3`、`GEMINI_RETRY_BASE_DELAY: float = 1.0`、`GEMINI_TIMEOUT_SECONDS: float = 30.0`
    - _Requirements: 11.1, 11.2, 9.4_
  - [x] 1.2 在 `backend/app/utils/datetime_helper.py` 新增 `build_date_range_query` 共用函式
    - 接收 `start_date`、`end_date`、`field_name` 參數，回傳 MongoDB 日期區間查詢 dict
    - _Requirements: 9.2_
  - [x] 1.3 建立 `backend/app/utils/validators.py`，實作 `validate_object_id` 工具函式
    - 使用 `bson.ObjectId.is_valid()` 驗證，無效時拋出 `HTTPException(400)`
    - _Requirements: 8.2, 10.1_

- [x] 2. AIService 非同步重構與重試/逾時機制
  - [x] 2.1 將 `backend/app/services/ai_service.py` 的 `_call_gemini` 改為 async，加入指數退避重試與 `asyncio.wait_for` 逾時
    - 僅對 HTTP 429/503 重試，使用 `settings.GEMINI_RETRY_MAX_ATTEMPTS`、`GEMINI_RETRY_BASE_DELAY`、`GEMINI_TIMEOUT_SECONDS`
    - 每次重試記錄日誌（attempt number + error）
    - 所有重試失敗後記錄最終錯誤並返回 None
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 9.3_
  - [x] 2.2 將 `perform_qa_answer_clustering`、`generate_response_draft`、`analyze_question`、`get_reply` 改為 async 並 await `_call_gemini`
    - _Requirements: 9.3_
  - [x] 2.3 優化 `perform_qa_answer_clustering` 的提示詞
    - 加入繁體中文輸出指令、電子商務領域指引、max_clusters 限制指令
    - 確保學生回答截斷至 300 字元
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  - [x] 2.4 更新 `backend/app/api/ai_integration.py` 中所有呼叫 AIService 的地方，加入 `await`
    - 包含 `generate_course_clusters`、`generate_response_draft` 等 endpoint
    - _Requirements: 9.3_

- [x] 3. Checkpoint — 確認 AIService 重構完成
  - Ensure all code compiles without errors, ask the user if questions arise.

- [x] 4. N+1 查詢消除與批次操作優化
  - [x] 4.1 重構 `backend/app/services/course_service.py` 的 `get_courses` 方法
    - 使用 aggregation pipeline 批次查詢 question_count 和 student_count，取代迴圈中逐筆 count_documents
    - _Requirements: 6.1_
  - [x] 4.2 重構 `backend/app/services/export_service.py` 的 `export_qas_to_csv` 方法
    - 使用單次 bulk query 取得所有 QA 的回覆，建立 qa_id → replies 映射，取代迴圈中逐筆 find
    - _Requirements: 6.2_
  - [x] 4.3 使用 `build_date_range_query` 重構 `export_service.py` 中重複的日期區間查詢邏輯
    - 替換 `export_questions_to_csv`、`export_qas_to_csv`、`export_statistics_to_csv` 中的重複程式碼
    - _Requirements: 9.2_
  - [x] 4.4 重構 `backend/app/api/questions.py` 的 `batch_update_review_status` endpoint
    - 使用單次 `update_many` 取代迴圈中逐筆 `update_review_status`
    - _Requirements: 6.3_

- [x] 5. 資料庫索引管理
  - [x] 5.1 在 `backend/app/database.py` 新增 `ensure_indexes` 類別方法
    - 建立 questions、clusters、qas、line_users 集合的索引（含複合索引）
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - [x] 5.2 在 `backend/app/main.py` 的 `lifespan` 中呼叫 `db.ensure_indexes()`
    - 在 `connect_db()` 之後、yield 之前呼叫
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 6. CORS 安全性加固與 ObjectId 驗證
  - [x] 6.1 修改 `backend/app/main.py` 的 CORS middleware 設定
    - `allow_methods` 改為 `["GET", "POST", "PATCH", "DELETE", "OPTIONS"]`
    - `allow_headers` 改為 `["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"]`
    - _Requirements: 10.2, 10.3_
  - [x] 6.2 在 `backend/app/api/questions.py` 的所有接收 ID 參數的 endpoint 加入 `validate_object_id` 驗證
    - 包含 `get_question`、`update_review_status`、`delete_question`、`get_questions_by_cluster`
    - _Requirements: 8.2, 10.1_
  - [x] 6.3 在 `backend/app/api/ai_integration.py` 的所有接收 ID 參數的 endpoint 加入 `validate_object_id` 驗證
    - 包含 `generate_course_clusters`（course_id, qa_id）、`get_clusters_summary`、`update_cluster`、`delete_cluster`
    - _Requirements: 8.2, 10.1_

- [x] 7. Checkpoint — 確認所有優化完成
  - Ensure all code compiles without errors, ask the user if questions arise.

- [x] 8. 測試基礎架構建立
  - [x] 8.1 建立 `backend/tests/__init__.py` 和 `backend/tests/conftest.py`
    - 設定 pytest-asyncio fixtures：mock MongoDB database、mock Gemini client、mock settings
    - 提供共用的 test data factory functions
    - _Requirements: 1.1, 3.1_
  - [x] 8.2 更新 `backend/requirements.txt`，新增 `hypothesis` 測試依賴
    - _Requirements: (testing infrastructure)_

- [x] 9. AI Service 單元測試與屬性測試
  - [x] 9.1 建立 `backend/tests/test_ai_service.py`，撰寫 AIService 單元測試
    - 測試空回答列表返回 `{"clusters": []}`（Req 2.4）
    - 測試 API Key 為空時拋出 ValueError（Req 3.3）
    - 測試 json_mode 設定 response_mime_type（Req 3.2）
    - 測試使用正確 model name（Req 3.1）
    - 測試 Gemini 回傳無效 JSON 時返回空 dict（Req 3.4）
    - 測試重試機制：429/503 觸發重試（Req 11.1）
    - 測試逾時機制：超過 30 秒拋出 TimeoutError（Req 11.2）
    - 測試所有重試失敗後返回 None 並記錄日誌（Req 11.3）
    - 測試重試時記錄 attempt number（Req 11.4）
    - 測試 async coroutine 驗證（Req 9.3）
    - _Requirements: 2.4, 3.1, 3.2, 3.3, 3.4, 9.3, 11.1, 11.2, 11.3, 11.4_
  - [ ]* 9.2 在 `test_ai_service.py` 撰寫 Property 4 屬性測試：提示詞建構完整性
    - **Property 4: Prompt construction completeness**
    - 使用 Hypothesis 生成隨機 teacher_question、core_concept、student_answers、existing_topics、max_clusters
    - 驗證提示詞包含所有必要元素
    - **Validates: Requirements 2.1, 2.2, 2.3, 12.3**
  - [ ]* 9.3 在 `test_ai_service.py` 撰寫 Property 5 屬性測試：無效 JSON 處理
    - **Property 5: Invalid JSON resilience**
    - 使用 Hypothesis 生成隨機非 JSON 字串
    - 驗證 `_call_gemini` 在 json_mode=True 時返回空 dict
    - **Validates: Requirements 3.4**
  - [ ]* 9.4 在 `test_ai_service.py` 撰寫 Property 11 屬性測試：回答截斷
    - **Property 11: Student answer truncation**
    - 使用 Hypothesis 生成隨機長度字串 (0-1000 字元)
    - 驗證提示詞中每個回答不超過 300 字元
    - **Validates: Requirements 12.4**

- [x] 10. 聚類管線整合測試
  - [x] 10.1 建立 `backend/tests/test_clustering_pipeline.py`，撰寫聚類管線整合測試
    - 測試完整聚類流程：取得回答 → 建構提示詞 → 呼叫 AI → 解析回應 → 寫入 DB
    - 測試無已審核回答時返回成功訊息（Req 5.1）
    - 測試 Gemini 401/403 錯誤處理（Req 5.2）
    - 測試 Gemini 異常時返回 HTTP 500（Req 5.3）
    - 測試 Gemini 回應缺少 clusters key 時拋出 ValueError（Req 4.4）
    - 測試 cluster document 正確寫入（Req 4.1, 4.2, 4.3）
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3_
  - [ ]* 10.2 在 `test_clustering_pipeline.py` 撰寫 Property 1 屬性測試：回覆篩選正確性
    - **Property 1: Reply filtering correctness**
    - 使用 Hypothesis 生成隨機 question documents（混合 review_status, cluster_id）
    - 驗證只返回 approved + cluster_id=None 的文件
    - **Validates: Requirements 1.1, 1.3**
  - [ ]* 10.3 在 `test_clustering_pipeline.py` 撰寫 Property 2 屬性測試：回覆輸出欄位完整性
    - **Property 2: Reply output shape**
    - 驗證返回的每個 reply 包含 `_id`, `pseudonym`, `answer_text`, `created_at`
    - **Validates: Requirements 1.2**
  - [ ]* 10.4 在 `test_clustering_pipeline.py` 撰寫 Property 3 屬性測試：回覆數量限制
    - **Property 3: Reply limit constraint**
    - 使用 Hypothesis 生成隨機 limit 值 (1-500)
    - 驗證返回數量 ≤ limit
    - **Validates: Requirements 1.4**
  - [ ]* 10.5 在 `test_clustering_pipeline.py` 撰寫 Property 6 屬性測試：聚類管線端到端正確性
    - **Property 6: Clustering pipeline end-to-end correctness**
    - 使用 Hypothesis 生成隨機 clustering response（valid indices, topic_labels）
    - 驗證 cluster documents 和 question updates 正確
    - **Validates: Requirements 4.1, 4.2, 4.3**

- [x] 11. N+1 消除驗證測試
  - [x] 11.1 建立 `backend/tests/test_n_plus_one.py`，撰寫 N+1 消除驗證測試
    - 測試 `get_courses` 使用 aggregation pipeline（Req 6.1）
    - 測試 `export_qas_to_csv` 使用 bulk query（Req 6.2）
    - 測試 `batch_update_review_status` 使用 update_many（Req 6.3）
    - _Requirements: 6.1, 6.2, 6.3_
  - [ ]* 11.2 在 `test_n_plus_one.py` 撰寫 Property 7 屬性測試：課程統計正確性
    - **Property 7: Course counts aggregation correctness**
    - 使用 Hypothesis 生成隨機 courses、questions、line_users documents
    - 驗證 question_count 和 student_count 正確
    - **Validates: Requirements 6.1**
  - [ ]* 11.3 在 `test_n_plus_one.py` 撰寫 Property 9 屬性測試：批次更新正確性
    - **Property 9: Batch update correctness**
    - 使用 Hypothesis 生成隨機 question IDs 與 review_status
    - 驗證所有指定文件的 review_status 被正確更新
    - **Validates: Requirements 6.3**

- [x] 12. 錯誤處理與索引測試
  - [x] 12.1 建立 `backend/tests/test_error_handling.py`，撰寫錯誤處理測試
    - 測試無效 ObjectId 返回 HTTP 400（Req 8.2, 10.1）
    - 測試 CORS 設定使用明確方法與標頭列表（Req 10.2, 10.3）
    - _Requirements: 8.2, 10.1, 10.2, 10.3_
  - [ ]* 12.2 在 `test_error_handling.py` 撰寫 Property 10 屬性測試：ObjectId 驗證
    - **Property 10: ObjectId validation**
    - 使用 Hypothesis 生成隨機無效 ObjectId 字串
    - 驗證 API endpoint 返回 HTTP 400
    - **Validates: Requirements 8.2, 10.1**
  - [x] 12.3 建立 `backend/tests/test_database_indexes.py`，撰寫索引驗證測試
    - 驗證 `ensure_indexes` 呼叫正確的 `create_index` 方法
    - 驗證所有預期索引被建立
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 13. Final checkpoint — 確認所有測試通過
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- 技術棧：Python 3.11+ / FastAPI / Motor (async MongoDB) / pytest + pytest-asyncio + hypothesis
