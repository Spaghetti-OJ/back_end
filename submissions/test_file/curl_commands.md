# 題解API快速測試命令

## 1. 獲取認證令牌
```bash
curl -X POST http://127.0.0.1:8000/auth/session/ \
  -H "Content-Type: application/json" \
  -d '{"username": "teacher1", "password": "testpass123"}'
```

## 2. 發布題解 (POST)
```bash
# 請先將上一步獲取的access token替換到 YOUR_JWT_TOKEN
curl -X POST http://127.0.0.1:8000/submissions/problem/1/solution/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "動態規劃解法",
    "content": "這個問題可以使用動態規劃來解決。首先定義狀態轉移方程，然後使用自底向上的方法填充DP表格。",
    "difficulty_rating": 3.5,
    "is_official": true
  }'
```

## 3. 獲取題解列表 (GET)
```bash
curl -X GET http://127.0.0.1:8000/submissions/problem/1/solution/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 4. 修改題解 (PUT)
```bash
# 請將 SOLUTION_UUID 替換為實際的題解ID (從創建響應中獲取)
curl -X PUT http://127.0.0.1:8000/submissions/problem/1/solution/SOLUTION_UUID/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "優化的動態規劃解法",
    "content": "經過優化的動態規劃解法，使用滾動數組技術將空間複雜度降低到O(1)。",
    "difficulty_rating": 4.0,
    "is_official": true
  }'
```

## 5. 刪除題解 (DELETE)
```bash
# 請將 SOLUTION_UUID 替換為實際的題解ID
curl -X DELETE http://127.0.0.1:8000/submissions/problem/1/solution/SOLUTION_UUID/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 錯誤測試

### 測試無效問題ID
```bash
curl -X GET http://127.0.0.1:8000/submissions/problem/999/solution/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 測試無認證請求
```bash
curl -X GET http://127.0.0.1:8000/submissions/problem/1/solution/
```

### 測試無效請求數據
```bash
curl -X POST http://127.0.0.1:8000/submissions/problem/1/solution/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "",
    "content": "短"
  }'
```

## 使用自動化測試腳本
如果您想要自動執行所有測試，可以運行：
```bash
./test_editorial_api.sh
```