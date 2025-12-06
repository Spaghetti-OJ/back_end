# /ranking API 文件（給前端）

此文件說明後端 `/ranking` API 的行為與前端使用方式。

## 概要
- 路徑：GET /ranking/
- 功能：回傳系統中所有使用者的投稿統計（NOJ-style）。
- 授權：此 API 需要驗證（必須登入）。
- 回傳格式採用專案內統一的 `api_response` 包裝：{ data, message, status }。

> 注意：Django 設定啟用了尾斜線自動轉向（APPEND_SLASH），請使用 `/ranking/` 或在請求時允許跟隨 301 重新導向。


## 權限
- 需要授權：請在請求標頭中帶上授權資訊（專案中使用 JWT 的話，請帶 `Authorization: Bearer <access_token>`）。
- 若未授權或權杖錯誤，會由 DRF 回傳 401/403（包在 `api_response` 裡），前端需處理對應錯誤。


## 範例：curl
未包含認證時（會被重導或回傳 401/403）：

```bash
# 注意尾斜線
curl -i http://127.0.0.1:8000/ranking/

# 帶 JWT 授權範例
curl -i -H "Authorization: Bearer <ACCESS_TOKEN>" http://127.0.0.1:8000/ranking/
```


## 成功回應範例
回傳成功範例如下（已由 `api_response` 包裝）：

```json
{
  "data": {
    "ranking": [
      {
        "user": {
          "id": 123,
          "username": "alice",
          "real_name": "Alice Lin",
          "email": "alice@example.com",
          "is_active": true,
          "date_joined": "2024-01-02T15:04:05"
        },
        "ACProblem": 10,
        "ACSubmission": 15,
        "Submission": 30
      },
      {
        "user": { /* ... */ },
        "ACProblem": 8,
        "ACSubmission": 12,
        "Submission": 25
      }
    ]
  },
  "message": "here you are, bro",
  "status": "ok"
}
```

說明：
- `data.ranking` 是陣列；每個元素代表一個使用者及該使用者的統計資料。
- `ACProblem`：該使用者 AC 過的不同題目數量（去重 problem_id）。
- `ACSubmission`：AC 的提交次數（status == '0'）。
- `Submission`：該使用者的總提交數量。


## 行為與前端注意事項
1. 後端目前會回傳「全部使用者」的資料，且**不做排序**（註：原始 NOJ 行為），因此前端若要顯示排行榜應在前端端做排序（例如依 ACProblem、ACSubmission 或自訂規則排序）。
2. 目前沒有分頁/限制，若使用者數量很多，回應可能很大。建議：
   - 若資料量可能爆增，請與後端協商加入分頁或 `limit`/`offset` 參數。
   - 或讓後端提供排序與分頁參數以減少傳輸量。
3. 性能：此 endpoint 會對每個使用者做多次聚合查詢（目前實作是逐一計算），有潛在效能問題。建議後端改進選項（供後端工程師參考）：
   - 在後端做一次聚合 Query（使用 annotate / aggregation）以減少查詢次數。
   - 定期以 background job 預計算排行榜並快取到 Redis。
   - 提供分頁與排序參數，或預先限制回傳人數（例如 top N）。
4. 快取：前端可以接受 10s~60s 的資料延遲（非即時）時，建議後端啟用快取並在完成新提交判題後更新/失效相關快取。


## 錯誤處理
- 權限錯誤（未授權或無權限）會回傳 `status` 為 `error` 且 `message` 含錯誤描述；前端應顯示適當提示並導向登入。
- 若後端發生例外，會回傳 500 與 `message` 提示（範例："Some error occurred, please contact the admin"）。


## 未來可改進（短清單）
- 為 `/ranking/` 支援分頁與排序參數（query param）。
- 增加後端快取（Redis）或預計算，減少即時查詢成本。
- 若前端只需 top-N，加上 `?limit=N` 支援以節省頻寬與時間。


---
檔案路徑：`back_end/docs/ranking.MD`
如需我把此內容同步加入 repo 並幫你 commit，或希望內容調整為英文/更精簡/加入示意圖，告訴我要做哪一種，我會接著處理。