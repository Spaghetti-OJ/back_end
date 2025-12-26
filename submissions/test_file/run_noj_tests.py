#!/usr/bin/env python3
"""
submissions/test_file/run_noj_tests.py - 運行 NOJ 兼容性測試

專門測試 NOJ 格式兼容性的測試運行器
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_django():
    """設置 Django 環境"""
    # 設置 Django 設定模組
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
    
    # 添加項目根目錄到 Python 路徑
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # 初始化 Django
    import django
    django.setup()


def run_noj_tests():
    """運行 NOJ 兼容性測試"""
    print("🚀 開始運行 NOJ 兼容性測試")
    print("=" * 60)
    
    # 項目根目錄
    project_root = Path(__file__).parent.parent.parent
    
    # 構建 pytest 命令
    cmd = [
        'python', '-m', 'pytest',
        'submissions/test_file/test_submission_noj_compatibility.py',
        '-v',                                  # 詳細輸出
        '--tb=short',                          # 簡短的錯誤追踪
        '--durations=10',                      # 顯示最慢的10個測試
    ]
    
    try:
        # 運行測試
        result = subprocess.run(cmd, cwd=project_root, check=False)
        
        if result.returncode == 0:
            print("\n✅ NOJ 兼容性測試全部通過！")
        else:
            print("\n❌ NOJ 兼容性測試失敗")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"\n❌ 發生錯誤：{e}")
        return False


if __name__ == '__main__':
    setup_django()
    run_noj_tests()