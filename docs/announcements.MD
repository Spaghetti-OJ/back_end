## 課程公告列表 API

**路徑**：`GET /ann/<course_id>/ann`

**說明**：取得指定課程的公告列表，會先依「是否置頂」再依更新時間（新 → 舊）排序。

**需要登入**（課程名稱為「公開討論區」時可免登入）

**URL 參數**

| 參數        | 說明           |
| ----------- | -------------- |
| `course_id` | 要查詢的課程 ID；公共討論區可使用 `0` |

**成功回應 (200 OK)**

```json
{
  "data": [
    {
      "annId": "9a056927-5f54-4cb7-9cd8-22d925fe8e24",
      "title": "系統維護通知",
      "createTime": 1732099200,
      "updateTime": 1732135200,
      "creator": {
        "id": "c1234f56-789a-4bde-b123-456789abcd12",
        "username": "admin01",
        "real_name": "系統管理員",
        "role": "admin"
      },
      "updater": {
        "id": "c1234f56-789a-4bde-b123-456789abcd12",
        "username": "admin01",
        "real_name": "系統管理員",
        "role": "admin"
      },
      "markdown": "### 系統維護\n今晚 23:00 ~ 23:30 將進行資料庫維護。",
      "pinned": true
    }
  ]
}
```

**備註**

- `createTime`、`updateTime` 以 Unix timestamp（秒）回傳。
- `creator` / `updater` 若已被刪除，欄位會回傳 `null`。
- 若找不到課程會回傳 `404 {"message": "Course not found."}`。
- 未登入時會回傳 `401`。
- 若該課程名稱為「公開討論區」，可直接存取（無須登入）。
- 公開討論區路徑可將 `course_id` 設為 `0` 代表系統公告（公開討論區）。

**cURL 測試**

```bash
curl http://127.0.0.1:8000/ann/<course_id>/ann \
    -H "Authorization: Bearer <access>"
```

---

- 若 `course_id` 對應的課程名稱為「公開討論區」，回傳結果即為原系統公告列表（前端僅需提供該課程的 ID 即可）。

---

## 課程公告建立 API

**路徑**：`POST /ann/`

**說明**：建立指定課程的公告。需要登入，且必須具備「GRADE 權限」——也就是課程的主要老師、課程成員老師 / TA，或系統管理員。

**需要登入**

**Body 參數**

| 欄位        | 型別   | 必填 | 說明                     |
| ----------- | ------ | ---- | ------------------------ |
| `title`     | string | ✅   | 公告標題，最長 200 字    |
| `content`   | string | ✅   | 公告內容（Markdown）     |
| `course_id` | int   | ✅   | 目標課程 ID（整數）              |
| `is_pinned` | bool   | ❌   | 是否置頂，預設為 `false` |

**成功回應 (201 Created)**

```json
{
  "data": {
    "annId": "新公告ID",
    "created_at": 1732099200
  }
}
```

**錯誤回應**

| 狀況                 | HTTP | 範例訊息                                |
| -------------------- | ---- | --------------------------------------- |
| 未登入               | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 權限不足             | 403  | `{ "message": "Permission denied." }` |
| 驗證錯誤 / 缺少欄位 | 400  | `{ "message": "Validation error.", "errors": { ... } }` |

## 課程公告更新 API

**路徑**：`PUT /ann/`

**說明**：更新指定公告的內容。需要登入並具備 GRADE 權限（課程老師、課程成員老師 / TA、系統管理員）。

**需要登入**

**Body 參數**

| 欄位        | 型別   | 必填 | 說明                                  |
| ----------- | ------ | ---- | ------------------------------------- |
| `annId`     | int    | ✅   | 要更新的公告 ID                       |
| `title`     | string | ✅   | 新標題                                |
| `context`   | string | ✅   | 新內容（Markdown，可改用 `content`） |
| `is_pinned` | bool   | ❌   | 是否置頂，不提供時維持原值            |

**成功回應 (200 OK)**

```json
{
  "message": "Updated"
}
```

**錯誤回應**

| 狀況         | HTTP | 範例訊息                              |
| ------------ | ---- | ------------------------------------- |
| 公告不存在   | 404  | `{ "message": "Announcement not found." }` |
| 權限不足     | 403  | `{ "message": "Permission denied." }` |
| 驗證錯誤     | 400  | `{ "message": "Validation error.", "errors": { ... } }` |

**cURL 測試**

```bash
curl -X PUT http://127.0.0.1:8000/ann/ \
    -H "Authorization: Bearer <access>" \
    -H "Content-Type: application/json" \
    -d '{
      "annId": 1,
      "title": "新標題",
      "context": "新內容",
      "is_pinned": true
    }'
```

## 課程公告刪除 API

**路徑**：`DELETE /ann/`

**說明**：刪除指定公告。需要登入並具備 GRADE 權限（課程老師、課程成員老師 / TA、系統管理員）。

**需要登入**

**Body 參數**

| 欄位    | 型別 | 必填 | 說明         |
| ------- | ---- | ---- | ------------ |
| `annId` | int  | ✅   | 要刪除的公告 ID |

**成功回應 (200 OK)**

```json
{
  "message": "Deleted"
}
```

**錯誤回應**

| 狀況         | HTTP | 範例訊息                              |
| ------------ | ---- | ------------------------------------- |
| 公告不存在   | 404  | `{ "message": "Announcement not found." }` |
| 權限不足     | 403  | `{ "message": "Permission denied." }` |
| 驗證錯誤     | 400  | `{ "message": "Validation error.", "errors": { ... } }` |

**cURL 測試**

```bash
curl -X DELETE http://127.0.0.1:8000/ann/ \
    -H "Authorization: Bearer <access>" \
    -H "Content-Type: application/json" \
    -d '{
      "annId": 1
    }'
```

## 課程公告詳情 API

**路徑**：`GET /ann/<course_id>/<ann_id>`

**說明**：取得指定課程中某一則公告，回傳欄位與列表 API 相同，但只包含符合 `ann_id` 的公告資料。

**需要登入**（課程名稱為「公開討論區」時可免登入）

**URL 參數**

| 參數        | 說明             |
| ----------- | ---------------- |
| `course_id` | 目標課程的 ID；公開討論區可使用 `0` |
| `ann_id`    | 要查詢的公告 ID |

**成功回應 (200 OK)**

```json
{
  "data": [
    {
      "annId": "9a056927-5f54-4cb7-9cd8-22d925fe8e24",
      "title": "系統維護通知",
      "createTime": 1732099200,
      "updateTime": 1732135200,
      "creator": {
        "id": "c1234f56-789a-4bde-b123-456789abcd12",
        "username": "admin01",
        "real_name": "系統管理員",
        "role": "admin"
      },
      "updater": {
        "id": "c1234f56-789a-4bde-b123-456789abcd12",
        "username": "admin01",
        "real_name": "系統管理員",
        "role": "admin"
      },
      "markdown": "### 系統維護\n今晚 23:00 ~ 23:30 將進行資料庫維護。",
      "pinned": true
    }
  ]
}
```

**備註**

- 若公告不存在會回傳 `404 {"message": "Announcement not found."}`。
- 其他狀況（登入、時間戳格式、創建者為 `null` 等）同列表 API。
- 若 `course_id` 對應的是名稱為「公開討論區」的課程，亦會回傳系統公告對應的資料。
- 若該課程名稱為「公開討論區」，可直接存取（無須登入）。
- 公開討論區路徑可將 `course_id` 設為 `0` 代表公開討論區。
- 本 API 與列表使用同一個 `SystemAnnouncementSerializer`，欄位完全一致。

**cURL 測試**

```bash
curl -X POST http://127.0.0.1:8000/ann/ \
    -H "Authorization: Bearer <access>" \
    -H "Content-Type: application/json" \
    -d '{
      "title": "標題",
      "content": "內容",
      "course_id": 42,
      "is_pinned": true
    }'
curl http://127.0.0.1:8000/ann/<course_id>/<ann_id> \
    -H "Authorization: Bearer <access>"
```
