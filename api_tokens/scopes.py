# api_tokens/scopes.py

class Scopes:
    """定義系統中所有可用的 API Token 權限範圍"""
    
    # 使用者相關
    READ_USER = "read:user"
    WRITE_USER = "write:user"
    
    # 題目相關
    READ_PROBLEMS = "read:problems"
    WRITE_PROBLEMS = "write:problems"
    
    # 作業相關
    READ_ASSIGNMENTS = "read:assignments"
    WRITE_ASSIGNMENTS = "write:assignments"
    
    # 提交相關
    READ_SUBMISSIONS = "read:submissions"
    WRITE_SUBMISSIONS = "write:submissions"
    SUBMIT = "submit"
    
    # 課程相關
    READ_COURSES = "read:courses"
    WRITE_COURSES = "write:courses"
    
    # 公告相關
    READ_ANNOUNCEMENTS = "read:announcements"
    WRITE_ANNOUNCEMENTS = "write:announcements"
    
    # 完整管理權限
    ADMIN = "admin"

    @classmethod
    def all_scopes(cls):
        """返回所有可用的 scopes"""
        return [
            value for name, value in vars(cls).items()
            if not name.startswith('_') and isinstance(value, str)
        ]
    
    @classmethod
    def get_description(cls, scope):
        """返回 scope 的描述"""
        descriptions = {
            cls.READ_USER: "讀取使用者資訊",
            cls.WRITE_USER: "修改使用者資訊",
            cls.READ_PROBLEMS: "讀取題目",
            cls.WRITE_PROBLEMS: "建立/修改題目",
            cls.READ_ASSIGNMENTS: "讀取作業",
            cls.WRITE_ASSIGNMENTS: "建立/修改作業",
            cls.READ_SUBMISSIONS: "讀取提交記錄",
            cls.WRITE_SUBMISSIONS: "修改提交記錄",
            cls.SUBMIT: "提交程式碼",
            cls.READ_COURSES: "讀取課程資訊",
            cls.WRITE_COURSES: "建立/修改課程",
            cls.READ_ANNOUNCEMENTS: "讀取公告",
            cls.WRITE_ANNOUNCEMENTS: "發布/修改公告",
            cls.ADMIN: "完整管理權限（包含所有操作）",
        }
        return descriptions.get(scope, "未知權限")
