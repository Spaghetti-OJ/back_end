# 後端 API 說明

本專案後端使用 **Django + Django REST Framework + Simple JWT**，所有 API 採 **JSON** 傳輸。

---

## 課程建立 API

**路徑**：`POST /course/`

**說明**：建立課程。

### 請求格式 (JSON)

| 欄位名             | 型別      | 必填 | 說明                            |
| --------------- | ------- | -- | ------------------------------- |
| `name`          | string  | ✅  | 課程名稱                          |
| `description`   | string  | ❌  | 課程說明                          |
| `student_limit` | integer | ✅  | 最多可加入的學生人數                    |
| `semester`      | string  | ✅  | 學期，例如 `"上學期"`                 |
| `academic_year` | integer | ✅  | 學年度，例如 `2025`                 |

---

**請求範例**

```json
{
    "name": "人工智慧導論",
    "description": "介紹 AI 基礎概念與應用",
    "student_limit": 60,
    "semester": "上學期",
    "academic_year": 2025
}
```

---

**成功回應 (201 Created)**

```json
{
  "id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12",
  "name": "人工智慧導論",
  "description": "介紹 AI 基礎概念與應用",
  "join_code": "A2BC3DE",
  "student_limit": 60,
  "semester": "上學期",
  "academic_year": 2025,
  "is_active": true,
  "student_count": 0,
  "created_at": "2025-10-12T06:45:30.251Z",
  "updated_at": "2025-10-12T06:45:30.251Z",
  "teacher": {
    "id": "c1234f56-789a-4bde-b123-456789abcd12",
    "username": "teacher01",
    "real_name": "王小明",
    "identity": "teacher"
  }
}
```

**失敗回應**

| 狀況            | HTTP | 範例訊息                                                            |
| ------------- | ---- | --------------------------------------------------------------- |
| 未登入           | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 權限不足          | 403  | `{ "detail": "只有老師或管理員可以建立課程。" }`                               |
| 欄位缺少          | 400  | `{ "name": ["This field is required."] }`                       |

**cURL 測試**：
```bash
curl -X POST http://127.0.0.1:8000/course/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access>" \
    -d '{
    "name": "人工智慧導論",
    "description": "介紹 AI 基礎概念與應用",
    "student_limit": 60,
    "semester": "上學期",
    "academic_year": 2025
    }'
```
