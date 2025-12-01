# 搜尋相關 API 說明

本專案後端使用 **Django + Django REST Framework + Simple JWT**，所有 API 採 **JSON** 傳輸。

> 所有端點（除個別標註外）都需要 `Authorization: Bearer <JWT access>`。  
> 本文件僅說明與「題目搜尋」相關的 API。

---

## 全域題目搜尋 API

路徑：GET `/search/`

說明：
- 根據關鍵字在「題目標題 (Problems.title)」與「標籤名稱 (Tags.name)」中進行全域搜尋。
- 僅回傳目前登入使用者**有權查看**的題目：
  - `is_public = "public"`：任何登入用戶皆可見。
  - `is_public = "course"`：僅該課程的老師 / TA / 修課學生可見。
  - `is_public = "hidden"`：僅出題者本人可見。

權限：需登入。

### 查詢參數（Query String）

| 參數名稱 | 型別   | 必填 | 說明                                                                 |
| -------- | ------ | :--: | -------------------------------------------------------------------- |
| q        | string |  ✅  | 關鍵字，會套用在 `Problems.title` 與 `Tags.name` 的模糊搜尋 (icontains)。 |

> 若 `q` 為空字串或未提供，後端會回傳 `items: []`、`total: 0`，並帶 `message = "keyword is empty"`。

### 成功回應（200 OK）

```jsonc
{
  "data": {
    "items": [
      {
        "id": 1,
        "title": "Tree Traversal",
        "difficulty": "medium",
        "max_score": 100,
        "is_public": "public",
        "total_submissions": 42,
        "accepted_submissions": 21,
        "acceptance_rate": "50.00",
        "like_count": 3,
        "view_count": 128,
        "total_quota": -1,
        "creator_id": "8c9a6a16-5d01-4c0a-8e43-xxxxxxxxxxxx",
        "course_id": 1,
        "course_name": "Data Structures 2025 Spring",
        "tags": [
          {
            "id": 10,
            "name": "tree",
            "usage_count": 5
          },
          {
            "id": 12,
            "name": "dfs",
            "usage_count": 3
          }
        ]
      }
    ],
    "total": 1
  },
  "message": "search problems success",
  "status": "ok"
}
```

- `data.items` 內每一筆物件對應到一個 `Problems` + 其關聯 `Tags`：  
  - `id`：`Problems.id` (int)  
  - `title`：`Problems.title`  
  - `difficulty`：`Problems.difficulty`，值為 `easy | medium | hard`  
  - `max_score`：`Problems.max_score`  
  - `is_public`：實際使用 `Problems.Visibility` 的三態字串：`hidden | course | public`  
  - `total_submissions` / `accepted_submissions` / `acceptance_rate` / `like_count` / `view_count` / `total_quota`：皆對應到 `Problems` 上同名欄位。
  - `creator_id`：`Users.id`（UUID，後端以 `creator_id_id` 取值並轉成字串）。  
  - `course_id`：`Courses.id`（目前為 int）。  
  - `course_name`：`Courses.__str__()`，方便前端直接顯示課程名稱。  
  - `tags`：該題目的所有 `Tags`，每個元素包含 `id`、`name`、`usage_count`。

### 可能錯誤回應

目前 `/search/` 僅在內部例外情況下才會回傳 500，正常情況：
- 未提供 `q`：依然回傳 200，`items` 為空、`message = "keyword is empty"`。

### cURL 測試範例

```bash
curl -X GET "http://127.0.0.1:8000/search/?q=tree"   -H "Authorization: Bearer <ACCESS_TOKEN>"   -H "Accept: application/json"
```

---

## 題目搜尋 API（含條件篩選）

路徑：GET `/search/problems`

說明：
- 在「使用者可見的題目集合」之內，提供更進一步的篩選條件。
- 可依關鍵字、難度、公開程度、課程、標籤等條件查詢。

權限：需登入。  
可見範圍與 `/search/` 相同：
- `public`：全部登入用戶皆可見。
- `course`：僅該課程老師 / TA / 修課學生可見（依 `Course_members` 與 `Courses.teacher_id` 判斷）。
- `hidden`：僅出題者本人可見。

### 查詢參數（Query String，全為選填）

| 參數名稱   | 型別   | 必填 | 說明                                                                 |
| ---------- | ------ | :--: | -------------------------------------------------------------------- |
| q          | string |  ❌  | 關鍵字，套用在題目標題與標籤名稱 (`title__icontains` / `tags__name__icontains`) |
| difficulty | string |  ❌  | 題目難度：`easy`、`medium`、`hard`                                  |
| is_public  | string |  ❌  | 題目可見性：`hidden`、`course`、`public`                            |
| course_id  | int    |  ❌  | 課程主鍵 `Courses.id`（目前實際為 **整數 PK**）                      |
| tag_id     | int    |  ❌  | 單一標籤 ID (`Tags.id`)                                             |

> **注意：**  
> - `course_id` 目前後端實際是以「整數 PK」查詢，若傳入非純數字（例如 UUID 字串），會回傳 400 錯誤。  
> - 未提供任何參數時，等同於回傳「所有你有權看到的題目」。

### 成功回應（200 OK）

結構與 `/search/` 相同：

```jsonc
{
  "data": {
    "items": [
      {
        "id": 1,
        "title": "Tree Traversal",
        "difficulty": "medium",
        "max_score": 100,
        "is_public": "course",
        "total_submissions": 42,
        "accepted_submissions": 21,
        "acceptance_rate": "50.00",
        "like_count": 3,
        "view_count": 128,
        "total_quota": -1,
        "creator_id": "8c9a6a16-5d01-4c0a-8e43-xxxxxxxxxxxx",
        "course_id": 1,
        "course_name": "Data Structures 2025 Spring",
        "tags": [
          {
            "id": 10,
            "name": "tree",
            "usage_count": 5
          }
        ]
      }
    ],
    "total": 1
  },
  "message": "search problems success",
  "status": "ok"
}
```

### 錯誤回應範例

- `course_id` 不是純數字（例如傳入 UUID 字串）：

```jsonc
{
  "data": {
    "items": [],
    "total": 0
  },
  "message": "invalid course_id format (expect integer id for now)",
  "status": "error"
}
```

> 目前 `tag_id` 若傳入無法轉成整數，會被 Django 自動視為查無資料，回傳空陣列並不會 500。

### cURL 測試範例

- 依關鍵字搜尋：

```bash
curl -X GET "http://127.0.0.1:8000/search/problems?q=tree"   -H "Authorization: Bearer <ACCESS_TOKEN>"   -H "Accept: application/json"
```

- 依課程 + 難度搜尋：

```bash
curl -X GET "http://127.0.0.1:8000/search/problems?q=tree&course_id=1&difficulty=easy"   -H "Authorization: Bearer <ACCESS_TOKEN>"   -H "Accept: application/json"
```

- 指定標籤與公開狀態：

```bash
curl -X GET "http://127.0.0.1:8000/search/problems?tag_id=10&is_public=public"   -H "Authorization: Bearer <ACCESS_TOKEN>"   -H "Accept: application/json"
```

---

以上兩支 API 的回傳結構都統一為：

```jsonc
{
  "data": {
    "items": [ /* 題目列表 */ ],
    "total": 0   // 題目總數
  },
  "message": "…",
  "status": "ok" | "error"
}
```

前端可以共用同一套型別定義與渲染邏輯。
