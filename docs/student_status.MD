# /stats/user/{userId} — 使用者統計（給前端）

此文件說明後端 `GET /stats/user/{userId}/` API 的行為與前端使用方式。

## 概要
- 路徑：GET /stats/user/{userId}/
- 功能：回傳單一使用者的統計資料（包含提交數、AC 統計、最佳分數、第一次 AC 時間等）。
- 授權：需要驗證（必須登入）。
- 回傳格式採用專案內統一的 `api_response` 包裝：{ data, message, status }。

> 注意：本 API 路徑建議末端加上 `/`（Django APPEND_SLASH 行為）。


## 權限與隱私（假設與約定）
- 預設行為（合理推定）：
  - 使用者本人可以取得自己的統計資料。
  - 管理員或擁有系統管理權限的帳號可以查看任意使用者的統計。
  - 若要允許老師/助教在課程範圍內查看學生資料，後端需以課程成員權限做授權判斷（此文件採開放式建議，具體權限請依實際後端實作為準）。
- 若你的權限策略不同，請告訴我要採用哪種：只有本人/本人+教師/僅 admin 等，我可以把文件改成精確敘述。


## 請求
- Method：GET
- URL 範例：
  - 取得自己：GET /stats/user/00000000-0000-0000-0000-000000000000/
  - 取得其他使用者（需權限）：GET /stats/user/{userId}/
- Headers：
  - Authorization: Bearer <ACCESS_TOKEN>
  - Accept: application/json


## 回傳欄位說明
最上層由 `api_response` 包裝，`data` 內為 `user_stats` 物件。以下為建議欄位：

- user: 基本使用者資訊（id, username, real_name, email, is_active, date_joined）
- total_submissions: 該使用者總提交數
- ac_submissions: AC（Accepted）提交次數（status == '0' 或 'accepted'，視系統實作）
- ac_problems: AC 的不同題目數（去重的 problem_id）
- best_score: 該使用者在系統上的最高分（若無則為 0）
- average_score: 平均分（可選）
- first_ac_time: 該使用者第一次 AC 的 timestamp（若無則為 null）
- last_submission_time: 最後一次提交時間
- acceptance_rate: 接受率（若後端計算）
- accept_percent: 接受率（百分比，0-100，若後端計算）
- other (可選): top_languages, solved_problem_list（視實作與隱私決定）


## 成功回應範例
```json
{
  "data": {
    "user_stats": {
      "user": {
        "id": "00000000-0000-0000-0000-000000000000",
        "username": "alice",
        "real_name": "Alice Lin",
        "email": "alice@example.com",
        "is_active": true,
        "date_joined": "2024-01-02T15:04:05"
      },
      "total_submissions": 123,
      "ac_submissions": 45,
      "ac_problems": 30,
      "best_score": 100,
      "average_score": 78.5,
      "first_ac_time": "2024-03-10T12:00:00",
      "last_submission_time": "2025-11-30T23:59:59",
      "accept_percent": 36.5
    }
  },
  "message": "user stats fetched",
  "status": "ok"
}
```

說明：
- `data.user_stats` 為主 payload，前端以此顯示使用者資料。
- 若某些欄位後端尚未提供（例如 `average_score`），會回傳 null 或不包含該欄位。


## 可能的錯誤回應
- 401 Unauthorized：未提供或失效的 token。
- 403 Forbidden：無權查看該使用者資料（例如：非本人且非 admin/teacher）。
- 404 Not Found：找不到目標使用者。
- 500 Internal Server Error：伺服器內部錯誤（前端可顯示一般錯誤訊息並上報）。

錯誤範例（未授權）：
```json
{
  "data": null,
  "message": "Authentication credentials were not provided.",
  "status": "error"
}
```


## 前端整合示例（fetch）
```js
async function fetchUserStats(userId, accessToken) {
  const res = await fetch(`/stats/user/${userId}/`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Accept': 'application/json'
    }
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    // 根據 statusCode 處理
    throw new Error(payload.message || `Fetch failed: ${res.status}`);
  }

  const payload = await res.json();
  return payload.data.user_stats; // 使用者統計物件
}
```
