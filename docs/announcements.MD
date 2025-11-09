## 課程公告列表 API

**路徑**：`GET /ann/<course_id>/ann`

**說明**：取得指定課程的公告列表，會先依「是否置頂」再依更新時間（新 → 舊）排序。

**需要登入**

**URL 參數**

| 參數        | 說明           |
| ----------- | -------------- |
| `course_id` | 要查詢的課程 ID |

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
        "identity": "admin"
      },
      "updater": {
        "id": "c1234f56-789a-4bde-b123-456789abcd12",
        "username": "admin01",
        "real_name": "系統管理員",
        "identity": "admin"
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

**cURL 測試**

```bash
curl http://127.0.0.1:8000/ann/<course_id>/ann \
    -H "Authorization: Bearer <access>"
```

---

- 若 `course_id` 對應的課程名稱為「公開討論區」，回傳結果即為原系統公告列表（前端僅需提供該課程的 ID 即可）。

## 課程公告詳情 API

**路徑**：`GET /ann/<course_id>/<ann_id>`

**說明**：取得指定課程中某一則公告，回傳欄位與列表 API 相同，但只包含符合 `ann_id` 的公告資料。

**需要登入**

**URL 參數**

| 參數        | 說明             |
| ----------- | ---------------- |
| `course_id` | 目標課程的 ID    |
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
        "identity": "admin"
      },
      "updater": {
        "id": "c1234f56-789a-4bde-b123-456789abcd12",
        "username": "admin01",
        "real_name": "系統管理員",
        "identity": "admin"
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
- 本 API 與列表使用同一個 `SystemAnnouncementSerializer`，欄位完全一致。

**cURL 測試**

```bash
curl http://127.0.0.1:8000/ann/<course_id>/<ann_id> \
    -H "Authorization: Bearer <access>"
```
