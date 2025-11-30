import mosspy
import os
import tempfile
from django.conf import settings
from .models import CopycatReport
from submissions.models import Submission
from django.core.exceptions import ImproperlyConfigured

try:
    MOSS_USER_ID = settings.MOSS_USER_ID
except AttributeError:
    raise ImproperlyConfigured("MOSS_USER_ID must be set in Django settings.")

MOSS_USER_ID = getattr(settings, 'MOSS_USER_ID', 123456789)

# 1. 語言映射表 (API 字串 -> 資料庫 Integer)
# 參考 Submission.LANGUAGE_CHOICES: 0=C, 1=C++, 2=Python, 3=Java, 4=JS
LANG_DB_MAP = {
    'c': 0,
    'cc': 1, 'cpp': 1, 'c++': 1,
    'python': 2, 'py': 2,
    'java': 3,
    'javascript': 4, 'js': 4
}

# 2. 檔案副檔名映射表 (API 字串 -> 檔案後綴)
LANG_EXT_MAP = {
    'c': '.c',
    'cc': '.cpp', 'cpp': '.cpp', 'c++': '.cpp',
    'python': '.py', 'py': '.py',
    'java': '.java',
    'javascript': '.js', 'js': '.js'
}

# 3. MOSS 支援的語言字串 (用於初始化 mosspy)
MOSSPY_LANG_MAP = {
    'c': 'c',
    'cc': 'cc', 'cpp': 'cc', 'c++': 'cc',
    'python': 'python', 'py': 'python',
    'java': 'java',
    'javascript': 'javascript', 'js': 'javascript'
}

def run_moss_check(report_id, problem_id, language='python'):
    """
    背景執行的 MOSS 檢測任務
    """
    print(f"[Copycat] 開始執行 MOSS 檢測 (Report: {report_id}, Problem: {problem_id}, Lang: {language})")
    
    try:
        
        report = CopycatReport.objects.get(id=report_id)
        lang_key = language.lower()
        
        if lang_key not in LANG_DB_MAP:
            raise ValueError(f"不支援的語言類型: {language}")

        target_db_val = LANG_DB_MAP[lang_key]      
        target_ext = LANG_EXT_MAP[lang_key]        
        target_moss_lang = MOSSPY_LANG_MAP[lang_key] 

        m = mosspy.Moss(MOSS_USER_ID, target_moss_lang)

        # 3. 從資料庫撈取 Submission
        raw_submissions = Submission.objects.filter(
            problem_id=problem_id,
            language_type=target_db_val
        ).select_related('user').order_by('-created_at')

        # 4. 過濾：只保留每位使用者的「最新」一份提交
        latest_submissions = {}
        for sub in raw_submissions:
            if sub.user_id not in latest_submissions:
                latest_submissions[sub.user_id] = sub
        
        final_list = list(latest_submissions.values())

        if len(final_list) < 2:
            raise Exception("提交數量不足 (至少需要 2 位不同的使用者才能比對)")

        print(f"[Copycat] 找到 {len(final_list)} 份有效提交 (已過濾重複使用者)...")

        # 5. 準備暫存檔案並加入 MOSS
        with tempfile.TemporaryDirectory() as temp_dir:
            for sub in final_list:
                file_name = f"{sub.user.username}_{sub.id}{target_ext}"
                file_path = os.path.join(temp_dir, file_name)
                
                with open(file_path, "w", encoding='utf-8') as f:
                    f.write(sub.source_code)
                
                m.addFile(file_path)

            # 6. 發送給 MOSS 伺服器
            print("[Copycat] 正在上傳至 MOSS 伺服器，請稍候...")
            url = m.send() 
            
            # 7. 更新資料庫
            print(f"[Copycat] 成功！報告網址: {url}")
            report.moss_url = url
            report.status = 'success'
            report.save()

    except Exception as e:
        print(f"[Copycat] 失敗: {e}")
        #report = CopycatReport.objects.get(id=report_id)
        report.status = 'failed'
        report.error_message = str(e)
        report.save()