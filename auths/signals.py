import ipaddress
import logging
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from .models import LoginLog

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """
    從 request 取得真實 IP 的輔助函式 (強化版)。
    驗證 IP 格式並處理多重代理的情況。
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        
        for ip in [ip.strip() for ip in x_forwarded_for.split(',')]:
            try:
                
                ipaddress.ip_address(ip)
                return ip
            except ValueError:
                continue
    
    ip = request.META.get('REMOTE_ADDR')
    try:
        ipaddress.ip_address(ip)
        return ip
    except Exception:
        return None

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    監聽：登入成功
    使用 try-except 包裹，避免日誌寫入失敗導致使用者無法登入
    """
    try:
        LoginLog.objects.create(
            user=user,
            username=user.username,
            login_status='success',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    except Exception as e:
        logger.error(f"Failed to create LoginLog for user {user.username}: {e}")

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """
    監聽：登入失敗
    """
    try:
        username = credentials.get('username', 'unknown')
        LoginLog.objects.create(
            user=None,
            username=username,
            login_status='failed_credentials',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    except Exception as e:
        logger.error(f"Failed to create failed LoginLog: {e}")