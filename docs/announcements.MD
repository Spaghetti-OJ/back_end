## 系統公告列表 API

**路徑**：`GET /ann/`

**說明**：取得系統公告列表，會先依「是否置頂」再依更新時間（新→舊）排序。

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

**cURL 測試**

```bash
curl http://127.0.0.1:8000/ann/
```
