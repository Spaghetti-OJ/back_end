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

## 作業排行榜 API

路徑：GET /homework/<homework_id>/scoreboard/

說明：回傳指定作業的排行榜資訊。

- `data` 物件內容：

    | 欄位          | 型別              | 說明                                 |
    | ------------- | ----------------- | ------------------------------------ |
    | homework_id   | int               | 作業 ID（對應 `Assignments.id`）     |
    | homework_title| string            | 作業標題（`Assignments.title`）      |
    | course_id     | uuid              | 課程 ID（`Assignments.course_id`）   |
    | items         | array<object>     | 排行榜每一列資料（每位學生一列）     |

- `items[]` 欄位（單一學生一列）：

    | 欄位                | 型別            | 說明                                                                 |
    | ------------------- | --------------- | -------------------------------------------------------------------- |
    | rank                | int             | 名次（依 `total_score` 由高到低、再比最早 AC 時間等規則排序後給定） |
    | user_id             | uuid            | 使用者 ID（`Users.id`）                                              |
    | username            | string          | 使用者帳號（`Users.username`）                                       |
    | real_name           | string          | 真實姓名（`Users.real_name`）                                        |
    | total_score         | int             | 此作業所有題目的總得分（各題 `best_score` 加總）                    |
    | max_total_score     | int             | 此作業理論滿分（各題 `max_possible_score` 加總）                     |
    | is_late             | boolean         | 是否有任何一題是「遲交」                                             |
    | first_ac_time       | string or null  | 最早 AC 時間（ISO 8601，若沒有 AC 則為 null）                        |
    | last_submission_time| string or null  | 最後一次提交時間（ISO 8601，若無提交則為 null）                      |
    | problems            | array<object>   | 此學生在本作業各題的詳細成績                                         |

- `items[].problems[]` 欄位（單一題目成績）：

    | 欄位              | 型別   | 說明                                      |
    | ----------------- | ------ | ----------------------------------------- |
    | problem_id        | int    | 題目 ID（`Problems.id`）                  |
    | best_score        | int    | 此學生在該題的最佳得分                    |
    | max_possible_score| int    | 該題的理論滿分                            |
    | solve_status      | string | 解題狀態：`"unsolved" / "partial" / "solved"` |

成功回應（200 OK）範例：

    {
      "data": {
        "homework_id": 1,
        "homework_title": "HW1 - Intro",
        "course_id": "469e303a-6d9e-4dda-831d-afe4c1ffdab5",
        "items": [
          {
            "rank": 1,
            "user_id": "0c224e53-9f94-46b6-af1e-0a226cf04072",
            "username": "momo",
            "real_name": "Momo",
            "total_score": 100,
            "max_total_score": 100,
            "is_late": false,
            "first_ac_time": "2025-11-15T12:34:56Z",
            "last_submission_time": "2025-11-15T12:34:56Z",
            "problems": [
              {
                "problem_id": 1,
                "best_score": 100,
                "max_possible_score": 100,
                "solve_status": "solved"
              }
            ]
          },
          {
            "rank": 2,
            "user_id": "554dea0c-16dc-4a49-afb7-897af80554e0",
            "username": "stu1",
            "real_name": "Student 1",
            "total_score": 80,
            "max_total_score": 100,
            "is_late": false,
            "first_ac_time": null,
            "last_submission_time": "2025-11-15T12:40:00Z",
            "problems": [
              {
                "problem_id": 1,
                "best_score": 80,
                "max_possible_score": 100,
                "solve_status": "partial"
              }
            ]
          }
        ]
      },
      "message": "get homework scoreboard",
      "status": "ok"
    }

錯誤回應：

- 作業不存在（404）：

      {
        "data": null,
        "message": "Not found.",
        "status": "error"
      }

- 未登入或 Token 無效（401 / 403）：

      {
        "data": null,
        "message": "Authentication credentials were not provided.",
        "status": "error"
      }

（實際訊息內容會依 DRF / SimpleJWT 設定而略有不同）

cURL 測試範例（Windows cmd，用 `%ACCESS_TOKEN%` 環境變數）： 

    curl -X GET "http://127.0.0.1:8000/homework/1/scoreboard/" ^
      -H "Authorization: Bearer %ACCESS_TOKEN%" ^
      -H "Accept: application/json"
