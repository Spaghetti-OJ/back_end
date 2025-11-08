"""
快取統計 Management Command

使用方式：
    python manage.py cache_stats
"""

from django.core.management.base import BaseCommand
from submissions.cache.monitoring import hit_rate_monitor


class Command(BaseCommand):
    help = 'Display cache hit rate statistics'
    
    def handle(self, *args, **options):
        """執行命令"""
        report = hit_rate_monitor.report()
        
        if not report:
            self.stdout.write(self.style.WARNING("No cache statistics available yet"))
            return
        
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("Cache Hit Rate Report"))
        self.stdout.write("=" * 70)
        
        for item in report:
            status_style = self.style.SUCCESS if item['status'] == 'OK' \
                          else self.style.WARNING if item['status'] == 'WARNING' \
                          else self.style.ERROR
            
            hit_rate_str = f"{item['hit_rate']:>6.1%}"
            self.stdout.write(
                f"[{item['status']}] {item['type']:<20} "
                f"Hit Rate: {status_style(hit_rate_str)}  "
                f"({item['hits']}/{item['total']})"
            )
        
        self.stdout.write("=" * 70 + "\n")
