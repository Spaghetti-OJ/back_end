from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from .models import LoginLog

def get_client_ip(request):
    """
    從 request 取得真實 IP 的輔助函式
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    監聽：登入成功
    動作：寫入 LoginLog (status='success')
    """
    LoginLog.objects.create(
        user=user,
        username=user.username,
        login_status='success',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """
    監聽：登入失敗
    動作：寫入 LoginLog (status='failed_credentials' 或其他)
    """
    username = credentials.get('username', 'unknown')
    
    LoginLog.objects.create(
        user=None, 
        username=username,
        login_status='failed_credentials',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )