# submissions/test_file/run_submission_api_tests.py - 運行所有 Submission API 測試的腳本
"""
便捷的測試運行腳本
可以運行所有 Submission API 相關的測試，或運行特定的測試類別
"""

import os
import sys
import subprocess
import django
from django.conf import settings

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()


def run_all_submission_tests():
    """運行所有 Submission API 測試"""
    print("🚀 運行所有 Submission API 測試...")
    
    test_commands = [
        # 模型測試
        'python -m pytest submissions/test_file/test_submission_models.py -v',
        
        # 序列化器測試
        'python -m pytest submissions/test_file/test_serializers.py::SubmissionSerializerHypothesisTests -v',
        
        # API Views 測試
        'python -m pytest submissions/test_file/test_submission_views_api.py -v',
        
        # 權限系統測試
        'python -m pytest submissions/test_file/test_submission_permissions.py -v',
    ]
    
    for cmd in test_commands:
        print(f"\n📋 執行: {cmd}")
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 測試通過")
        else:
            print("❌ 測試失敗")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
    
    print("\n🎉 所有測試完成！")
    return True


def run_api_tests_only():
    """只運行 API 測試"""
    print("🎯 運行 API Views 測試...")
    
    cmd = 'python -m pytest submissions/test_file/test_submission_views_api.py -v --tb=short'
    result = subprocess.run(cmd.split())
    return result.returncode == 0


def run_permission_tests_only():
    """只運行權限測試"""
    print("🔒 運行權限系統測試...")
    
    cmd = 'python -m pytest submissions/test_file/test_submission_permissions.py -v --tb=short'
    result = subprocess.run(cmd.split())
    return result.returncode == 0


def run_specific_test_class(test_class_name):
    """運行特定的測試類"""
    print(f"🎯 運行特定測試類: {test_class_name}")
    
    # 在所有測試文件中搜索測試類
    test_files = [
        'submissions/test_file/test_submission_views_api.py',
        'submissions/test_file/test_submission_permissions.py',
    ]
    
    for test_file in test_files:
        cmd = f'python -m pytest {test_file}::{test_class_name} -v --tb=short'
        print(f"嘗試在 {test_file} 中運行 {test_class_name}...")
        
        result = subprocess.run(cmd.split())
        if result.returncode == 0:
            print(f"✅ 在 {test_file} 中找到並運行了 {test_class_name}")
            return True
    
    print(f"❌ 找不到測試類 {test_class_name}")
    return False


def show_available_tests():
    """顯示可用的測試類"""
    print("📋 可用的測試類：")
    
    test_classes = [
        # API Views 測試
        "TestSubmissionCreateAPI - 測試創建提交",
        "TestSubmissionCodeUploadAPI - 測試上傳程式碼", 
        "TestSubmissionListAPI - 測試提交列表",
        "TestSubmissionDetailAPI - 測試提交詳情",
        "TestSubmissionCodeAPI - 測試獲取程式碼",
        "TestSubmissionStdoutAPI - 測試獲取輸出",
        "TestSubmissionRejudgeAPI - 測試重新判題",
        "TestRankingAPI - 測試排行榜",
        "TestSubmissionPermissionEdgeCases - 測試權限邊界情況",
        
        # 權限系統測試
        "BasePermissionMixinUnitTests - 權限系統單元測試",
        "PermissionIntegrationTests - 權限系統整合測試",
    ]
    
    for i, test_class in enumerate(test_classes, 1):
        print(f"  {i}. {test_class}")


def run_coverage_report():
    """生成測試覆蓋率報告"""
    print("📊 生成測試覆蓋率報告...")
    
    cmd = [
        'python', '-m', 'pytest',
        'submissions/test_file/test_submission_views_api.py',
        'submissions/test_file/test_submission_permissions.py',
        '--cov=submissions.views',
        '--cov=submissions.serializers', 
        '--cov-report=html',
        '--cov-report=term',
        '-v'
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n📋 覆蓋率報告已生成！")
        print("HTML 報告位置: htmlcov/index.html")
    
    return result.returncode == 0


def main():
    """主函數 - 提供交互式菜單"""
    if len(sys.argv) > 1:
        # 命令行參數模式
        arg = sys.argv[1]
        
        if arg == '--all':
            return run_all_submission_tests()
        elif arg == '--api':
            return run_api_tests_only()
        elif arg == '--permissions':
            return run_permission_tests_only()
        elif arg == '--coverage':
            return run_coverage_report()
        elif arg == '--list':
            show_available_tests()
            return True
        elif arg.startswith('--class='):
            class_name = arg.split('=')[1]
            return run_specific_test_class(class_name)
        else:
            print("❌ 未知參數。使用 --help 查看可用選項。")
            return False
    
    # 交互式菜單模式
    while True:
        print("\n" + "="*50)
        print("🧪 Submission API 測試運行器")
        print("="*50)
        print("1. 運行所有測試")
        print("2. 只運行 API Views 測試")
        print("3. 只運行權限系統測試")
        print("4. 運行特定測試類")
        print("5. 顯示可用測試類")
        print("6. 生成覆蓋率報告")
        print("0. 退出")
        
        choice = input("\n請選擇 (0-6): ").strip()
        
        if choice == '0':
            print("👋 再見！")
            break
        elif choice == '1':
            run_all_submission_tests()
        elif choice == '2':
            run_api_tests_only()
        elif choice == '3':
            run_permission_tests_only()
        elif choice == '4':
            test_class = input("請輸入測試類名稱: ").strip()
            if test_class:
                run_specific_test_class(test_class)
        elif choice == '5':
            show_available_tests()
        elif choice == '6':
            run_coverage_report()
        else:
            print("❌ 無效選擇，請重新選擇。")


def print_usage():
    """打印使用說明"""
    print("""
🧪 Submission API 測試運行器使用說明

命令行模式：
  python run_submission_api_tests.py --all          # 運行所有測試
  python run_submission_api_tests.py --api          # 只運行 API 測試
  python run_submission_api_tests.py --permissions  # 只運行權限測試
  python run_submission_api_tests.py --coverage     # 生成覆蓋率報告
  python run_submission_api_tests.py --list         # 顯示可用測試類
  python run_submission_api_tests.py --class=TestSubmissionCreateAPI  # 運行特定測試類

交互式模式：
  python run_submission_api_tests.py               # 啟動交互式菜單

測試標記：
  @pytest.mark.django_db    - 需要數據庫的測試
  @pytest.mark.unit        - 單元測試
  @pytest.mark.integration - 整合測試
  @pytest.mark.hypothesis  - 屬性基礎測試
""")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print_usage()
    else:
        main()