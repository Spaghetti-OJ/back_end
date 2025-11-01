#!/bin/bash

# 題解API測試腳本
# 使用方法: ./test_editorial_api.sh

BASE_URL="http://127.0.0.1:8000"
PROBLEM_ID=1

echo "=== 題解API測試腳本 ==="
echo "基礎URL: $BASE_URL"
echo "測試問題ID: $PROBLEM_ID"
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 步驟1: 獲取認證令牌
echo -e "${BLUE}步驟1: 獲取認證令牌${NC}"
echo "curl -X POST $BASE_URL/auth/session/ \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"username\": \"teacher1\", \"password\": \"testpass123\"}'"
echo ""

TOKEN_RESPONSE=$(curl -s -X POST $BASE_URL/auth/session/ \
  -H "Content-Type: application/json" \
  -d '{"username": "teacher1", "password": "testpass123"}')

echo "響應: $TOKEN_RESPONSE"

# 從響應中提取access token
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${RED}錯誤: 無法獲取認證令牌，請檢查用戶名和密碼${NC}"
    echo "請確保:"
    echo "1. Django服務器正在運行 (python manage.py runserver 8000)"
    echo "2. 用戶 teacher1 存在且密碼正確"
    exit 1
fi

echo -e "${GREEN}成功獲取認證令牌${NC}"
echo "Token: ${ACCESS_TOKEN:0:50}..."
echo ""

# 步驟2: 發布題解 (POST)
echo -e "${BLUE}步驟2: 發布題解 (POST)${NC}"
echo "curl -X POST $BASE_URL/submissions/problem/$PROBLEM_ID/solution/ \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -H \"Authorization: Bearer \$ACCESS_TOKEN\" \\"
echo "  -d '{...}'"
echo ""

CREATE_RESPONSE=$(curl -s -X POST $BASE_URL/submissions/problem/$PROBLEM_ID/solution/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "title": "動態規劃解法",
    "content": "這個問題可以使用動態規劃來解決。首先定義狀態轉移方程，然後使用自底向上的方法填充DP表格。時間複雜度為O(n^2)，空間複雜度為O(n)。",
    "difficulty_rating": 3.5,
    "is_official": true
  }')

echo "響應: $CREATE_RESPONSE"

# 從響應中提取solution ID
SOLUTION_ID=$(echo $CREATE_RESPONSE | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$SOLUTION_ID" ]; then
    echo -e "${RED}錯誤: 無法創建題解，請檢查響應${NC}"
    echo ""
else
    echo -e "${GREEN}成功創建題解${NC}"
    echo "題解ID: $SOLUTION_ID"
    echo ""
fi

# 步驟3: 獲取題解列表 (GET)
echo -e "${BLUE}步驟3: 獲取題解列表 (GET)${NC}"
echo "curl -X GET $BASE_URL/submissions/problem/$PROBLEM_ID/solution/ \\"
echo "  -H \"Authorization: Bearer \$ACCESS_TOKEN\""
echo ""

LIST_RESPONSE=$(curl -s -X GET $BASE_URL/submissions/problem/$PROBLEM_ID/solution/ \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "響應: $LIST_RESPONSE"
echo ""

# 步驟4: 修改題解 (PUT) - 只有在成功創建題解時執行
if [ ! -z "$SOLUTION_ID" ]; then
    echo -e "${BLUE}步驟4: 修改題解 (PUT)${NC}"
    echo "curl -X PUT $BASE_URL/submissions/problem/$PROBLEM_ID/solution/$SOLUTION_ID/ \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -H \"Authorization: Bearer \$ACCESS_TOKEN\" \\"
    echo "  -d '{...}'"
    echo ""

    UPDATE_RESPONSE=$(curl -s -X PUT $BASE_URL/submissions/problem/$PROBLEM_ID/solution/$SOLUTION_ID/ \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -d '{
        "title": "優化的動態規劃解法",
        "content": "經過優化的動態規劃解法，使用滾動數組技術將空間複雜度降低到O(1)。這種方法在處理大型數據集時更有效率。具體實現步驟如下：1. 初始化兩個變量代替整個DP數組 2. 在每次迭代中更新這兩個變量 3. 最終返回結果",
        "difficulty_rating": 4.0,
        "is_official": true
      }')

    echo "響應: $UPDATE_RESPONSE"
    echo ""

    # 步驟5: 刪除題解 (DELETE)
    echo -e "${BLUE}步驟5: 刪除題解 (DELETE)${NC}"
    echo "curl -X DELETE $BASE_URL/submissions/problem/$PROBLEM_ID/solution/$SOLUTION_ID/ \\"
    echo "  -H \"Authorization: Bearer \$ACCESS_TOKEN\""
    echo ""

    DELETE_RESPONSE=$(curl -s -w "%{http_code}" -X DELETE $BASE_URL/submissions/problem/$PROBLEM_ID/solution/$SOLUTION_ID/ \
      -H "Authorization: Bearer $ACCESS_TOKEN")

    echo "HTTP狀態碼: $DELETE_RESPONSE"
    
    if [ "$DELETE_RESPONSE" = "204" ]; then
        echo -e "${GREEN}成功刪除題解${NC}"
    else
        echo -e "${RED}刪除題解失敗${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}跳過修改和刪除測試（因為題解創建失敗）${NC}"
    echo ""
fi

# 額外測試: 錯誤情況
echo -e "${BLUE}步驟6: 錯誤情況測試${NC}"

# 測試無效的problem ID
echo "6.1 測試無效的問題ID (999):"
curl -s -X GET $BASE_URL/submissions/problem/999/solution/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo ""

# 測試無效的solution ID
echo "6.2 測試無效的題解ID:"
curl -s -X PUT $BASE_URL/submissions/problem/$PROBLEM_ID/solution/invalid-uuid/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"title": "test", "content": "test content for testing"}'
echo ""

# 測試無認證請求
echo "6.3 測試無認證請求:"
curl -s -X GET $BASE_URL/submissions/problem/$PROBLEM_ID/solution/
echo ""

# 測試無效的請求數據
echo "6.4 測試無效的請求數據 (標題太長):"
curl -s -X POST $BASE_URL/submissions/problem/$PROBLEM_ID/solution/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "title": "'$(python3 -c "print('a' * 300)")'",
    "content": "valid content"
  }'
echo ""

echo -e "${GREEN}=== API測試完成 ===${NC}"