import mosspy
import os
import tempfile
import logging
from django.conf import settings
from .models import CopycatReport
from submissions.models import Submission
from django.core.exceptions import ImproperlyConfigured

try:
    MOSS_USER_ID = settings.MOSS_USER_ID
except AttributeError:
    raise ImproperlyConfigured("MOSS_USER_ID must be set in Django settings.")

logger = logging.getLogger(__name__)


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
    logger.info(f"[Copycat] 開始執行 MOSS 檢測 (Report: {report_id}, Problem: {problem_id}, Lang: {language})")
    
    report = None
    
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

        logger.info(f"[Copycat] 找到 {len(final_list)} 份有效提交 (已過濾重複使用者)...")

        # 5. 準備暫存檔案並加入 MOSS
        with tempfile.TemporaryDirectory() as temp_dir:
            for sub in final_list:
                file_name = f"{sub.user.username}_{sub.id}{target_ext}"
                file_path = os.path.join(temp_dir, file_name)
                
                with open(file_path, "w", encoding='utf-8') as f:
                    f.write(sub.source_code)
                
                m.addFile(file_path)

            # 6. 發送給 MOSS 伺服器
            logger.info("[Copycat] 正在上傳至 MOSS 伺服器，請稍候...")
            url = m.send() 
            
            # 7. 更新資料庫
            logger.info(f"[Copycat] 成功！報告網址: {url}")
            report.moss_url = url
            report.status = 'success'
            report.save()

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Copycat] 任務失敗: {error_msg}")
        # report = CopycatReport.objects.get(id=report_id) 
        #try-except以防report物件失效
        try:
            if report:
                report.refresh_from_db()  # 確保獲取最新狀態 (避免覆蓋其他欄位)
                report.status = 'failed'
                report.error_message = error_msg
                report.save()
            else:
                # 如果 report 一開始就沒抓到 (例如被刪了)，嘗試重新獲取
                report = CopycatReport.objects.get(id=report_id)
                report.status = 'failed'
                report.error_message = error_msg
                report.save()
                
        except CopycatReport.DoesNotExist:
            logger.warning(f"[Copycat] 報告 {report_id} 已被刪除，無法更新失敗狀態")
        except Exception as db_error:
            logger.error(f"[Copycat] 無法更新報告狀態 (DB Error): {db_error}")