# 後端 API 說明

本專案後端使用 **Django + Django REST Framework + Simple JWT**，所有 API 採 **JSON** 傳輸。

> 所有端點（除個別標註外）都需要 Authorization: Bearer <JWT access>。

---

## 課程作業列表

路徑：GET /course/<uuid:course_id>/homework/

說明：回傳指定課程底下所有作業清單（依 `make_list_item_from_instance` 輸出結構）。

成功回應（200 OK）：

    {
      "message": "get homeworks",
      "items": [
        {
          "id": 1,
          "name": "HW1 - Intro",
          "start": null,
          "end": null,
          "problemIds": [101, 102],
          "markdown": "第一份作業內容",
          "studentStatus": "teacher_or_ta"
        }
      ]
    }

找不到課程（404）：

    "course not exists"

cURL 測試範例：

    curl -X GET "http://127.0.0.1:8000/course/<COURSE_UUID>/homework/" ^
      -H "Authorization: Bearer <ACCESS_TOKEN>" ^
      -H "Accept: application/json"

---

## 建立作業 API

路徑：POST /homework/

權限：需登入，且必須為該課程之老師或助教。

請求格式（JSON）：

| 欄位         | 型別           | 必填 | 說明                                        |
| ------------ | -------------- | :--: | ------------------------------------------- |
| name         | string         |  ✅  | 作業名稱（同課程內不可重複）                |
| markdown     | string         |  ❌  | 作業說明                                    |
| course_id    | uuid           |  ✅  | 所屬課程 ID                                 |
| start        | string or null |  ❌  | 開始時間（ISO 8601；後端轉為 `_start_dt`）  |
| end          | string or null |  ❌  | 結束時間（ISO 8601；後端轉為 `_end_dt`）    |
| problem_ids  | array<int>     |  ❌  | 題目 ID 列表（會依序建立 `order_index`）    |

請求範例：

    {
      "name": "HW1 - Intro",
      "markdown": "第一份作業內容",
      "course_id": "4e3e0a4e-6a75-48da-b692-291c65186ce3",
      "start": null,
      "end": null,
      "problem_ids": [101, 102]
    }

成功回應（200）：

    "Add homework Success"

錯誤回應：
- 400 名稱重複：

      "homework exists in this course"

- 403 權限不足（非老師或助教）：

      "user must be the teacher or ta of this course"

cURL 測試範例：

    curl -X POST "http://127.0.0.1:8000/homework/" ^
      -H "Authorization: Bearer <ACCESS_TOKEN>" ^
      -H "Content-Type: application/json" ^
      -d "{
        \"name\": \"HW1 - Intro\",
        \"markdown\": \"第一份作業內容\",
        \"course_id\": \"<COURSE_UUID>\",
        \"problem_ids\": [101, 102]
      }"

---

## 取得作業詳情 API

路徑：GET /homework/<homework_id>/

說明：回傳單一作業詳情（由 `HomeworkDetailSerializer.from_instance(...)` 生成）。

成功回應（200 OK）：

    {
      "message": "get homework",
      "name": "HW1 - Intro",
      "start": null,
      "end": null,
      "problemIds": [101, 102],
      "markdown": "第一份作業內容",
      "studentStatus": "teacher_or_ta",
      "penalty": ""
    }

找不到（404）：（DEBUG=False 通常為）

    {"detail": "Not found."}

cURL 測試範例：

    curl -X GET "http://127.0.0.1:8000/homework/<HW_ID>/" ^
      -H "Authorization: Bearer <ACCESS_TOKEN>" ^
      -H "Accept: application/json"

---

## 更新作業 API

路徑：PUT /homework/<homework_id>/

權限：需登入，且必須為該課程之老師或助教。

請求格式（JSON；皆為選填，僅提供要更新的欄位）：

| 欄位         | 型別           | 說明                                                     |
| ------------ | -------------- | -------------------------------------------------------- |
| name         | string         | 新作業名稱（與同課程其他作業重名時回 400）               |
| markdown     | string         | 新作業說明                                               |
| start        | string or null | 新開始時間（ISO 8601；後端轉 `_start_dt`）               |
| end          | string or null | 新結束時間（ISO 8601；後端轉 `_end_dt`）                 |
| problem_ids  | array<int>     | 重新指定題目（會先刪除舊綁定，再依序重建 `order_index`） |

成功回應（200）：

    "Update homework Success"

錯誤回應：
- 400 名稱重複：

      "homework exists in this course"

- 403 權限不足：

      "user must be the teacher or ta of this course"

- 404 作業不存在：同「取得作業詳情」404

cURL 測試範例：

    curl -X PUT "http://127.0.0.1:8000/homework/<HW_ID>/" ^
      -H "Authorization: Bearer <ACCESS_TOKEN>" ^
      -H "Content-Type: application/json" ^
      -d "{
        \"name\": \"HW1 - Updated\",
        \"problem_ids\": [201, 202]
      }"

---

## 刪除作業 API

路徑：DELETE /homework/<homework_id>/

權限：需登入，且必須為該課程之老師或助教。

成功回應（200）：

    "Delete homework Success"

錯誤回應：
- 403 權限不足：

      "user must be the teacher or ta of this course"

- 404 作業不存在：同「取得作業詳情」404

cURL 測試範例：

    curl -X DELETE "http://127.0.0.1:8000/homework/<HW_ID>/" ^
      -H "Authorization: Bearer <ACCESS_TOKEN>"


