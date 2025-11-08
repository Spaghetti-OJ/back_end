"""
Redis 記憶體監控 Management Command

使用方式：
    python manage.py monitor_redis_memory
"""

from django.core.management.base import BaseCommand
from submissions.cache.monitoring import memory_monitor


class Command(BaseCommand):
    help = 'Monitor Redis memory usage'
    
    def handle(self, *args, **options):
        """執行命令"""
        info = memory_monitor.check_and_alert()
        
        if not info:
            self.stdout.write(self.style.ERROR("[ERROR] Failed to get Redis memory info"))
            self.stdout.write("Make sure Redis is running and properly configured")
            return
        
        status = info['status']
        status_style = self.style.SUCCESS if status == 'OK' \
                      else self.style.WARNING if status == 'WARNING' \
                      else self.style.ERROR
        
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(status_style(f"Redis Memory Status: {status}"))
        self.stdout.write("=" * 70)
        
        self.stdout.write(
            f"Used Memory:  {info['used_memory_mb']:.1f} MB"
        )
        self.stdout.write(
            f"Max Memory:   {info['max_memory_mb']:.1f} MB"
        )
        usage_ratio_str = f"{info['usage_ratio']:.1%}"
        self.stdout.write(
            f"Usage Ratio:  {status_style(usage_ratio_str)}"
        )
        
        self.stdout.write("=" * 70 + "\n")
        
        # 提供建議
        if status == 'CRITICAL':
            self.stdout.write(self.style.ERROR("[CRITICAL] Memory usage is very high!"))
            self.stdout.write("Recommended actions:")
            self.stdout.write("  1. Increase Redis maxmemory")
            self.stdout.write("  2. Check for cache key leaks")
            self.stdout.write("  3. Verify eviction policy is working")
        elif status == 'WARNING':
            self.stdout.write(self.style.WARNING("[WARNING] Memory usage is high"))
            self.stdout.write("Consider monitoring closely or increasing maxmemory")
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Memory usage is healthy"))
