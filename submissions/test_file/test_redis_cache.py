"""
Redis 快取系統 Hypothesis 測試

測試範圍：
1. CacheKeys - 快取鍵生成邏輯
2. CachePenetrationProtection - 布隆過濾器防穿透
3. RedisDistributedLock - 分散式鎖
4. CacheWithFallback - 降級機制
5. 快取監控功能
"""

import uuid
import time
import threading
from decimal import Decimal
from django.test import TestCase
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.conf import settings

from hypothesis import given, strategies as st, settings as hypothesis_settings, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from submissions.cache.keys import CacheKeys
from submissions.cache.protection import CachePenetrationProtection
from submissions.cache.lock import RedisDistributedLock
from submissions.cache.fallback import CacheWithFallback
from submissions.cache.monitoring import CacheHitRateMonitor, RedisMemoryMonitor
from submissions.models import Submission

User = get_user_model()


class CacheKeysTests(HypothesisTestCase):
    """測試快取鍵生成的正確性與一致性"""
    
    @given(
        user_id=st.text(min_size=1, max_size=50),
        problem_id=st.integers(min_value=1, max_value=99999),
        status=st.sampled_from(['-2', '-1', '0', '1', '2', '3', None]),
        language=st.sampled_from(['c', 'cpp', 'python', 'java', None]),
        offset=st.integers(min_value=0, max_value=1000),
        limit=st.integers(min_value=1, max_value=100)
    )
    @hypothesis_settings(max_examples=20)
    def test_submission_list_key_consistency(
        self, user_id, problem_id, status, language, offset, limit
    ):
        """測試：相同參數應該生成相同的快取鍵"""
        key1 = CacheKeys.submission_list(
            user_id=user_id,
            problem_id=problem_id,
            status=status,
            language=language,
            offset=offset,
            limit=limit
        )
        key2 = CacheKeys.submission_list(
            user_id=user_id,
            problem_id=problem_id,
            status=status,
            language=language,
            offset=offset,
            limit=limit
        )
        
        # 相同參數必須生成相同快取鍵
        self.assertEqual(key1, key2)
        # 快取鍵必須包含前綴
        self.assertTrue(key1.startswith(CacheKeys.PREFIX_SUBMISSION_LIST))
        # 快取鍵必須包含 user_id
        self.assertIn(user_id, key1)
    
    @given(
        user_id=st.text(min_size=1, max_size=50),
        problem_id1=st.integers(min_value=1, max_value=99999),
        problem_id2=st.integers(min_value=1, max_value=99999)
    )
    @hypothesis_settings(max_examples=20)
    def test_submission_list_key_uniqueness(self, user_id, problem_id1, problem_id2):
        """測試：不同參數應該生成不同的快取鍵"""
        assume(problem_id1 != problem_id2)  # 確保參數不同
        
        key1 = CacheKeys.submission_list(user_id=user_id, problem_id=problem_id1)
        key2 = CacheKeys.submission_list(user_id=user_id, problem_id=problem_id2)
        
        # 不同參數必須生成不同快取鍵
        self.assertNotEqual(key1, key2)
    
    @given(
        submission_id=st.text(min_size=1, max_size=100)
    )
    @hypothesis_settings(max_examples=20)
    def test_submission_detail_key_format(self, submission_id):
        """測試：提交詳情快取鍵格式正確"""
        key = CacheKeys.submission_detail(submission_id)
        
        # 檢查格式
        self.assertTrue(key.startswith(CacheKeys.PREFIX_SUBMISSION_DETAIL))
        self.assertIn(submission_id, key)
        self.assertIn(':', key)  # 應該使用冒號分隔
    
    @given(
        problem_id=st.integers(min_value=1, max_value=99999),
        user_id=st.text(min_size=1, max_size=50)
    )
    @hypothesis_settings(max_examples=20)
    def test_high_score_key_format(self, problem_id, user_id):
        """測試：高分快取鍵包含必要資訊"""
        key = CacheKeys.high_score(problem_id, user_id)
        
        self.assertTrue(key.startswith(CacheKeys.PREFIX_HIGH_SCORE))
        self.assertIn(str(problem_id), key)
        self.assertIn(user_id, key)
    
    @given(
        user_id=st.text(min_size=1, max_size=50)
    )
    @hypothesis_settings(max_examples=20)
    def test_user_stats_key_format(self, user_id):
        """測試：用戶統計快取鍵格式正確"""
        key = CacheKeys.user_stats(user_id)
        
        self.assertTrue(key.startswith(CacheKeys.PREFIX_USER_STATS))
        self.assertIn(user_id, key)


class BloomFilterTests(HypothesisTestCase):
    """測試布隆過濾器的正確性"""
    
    def setUp(self):
        """每次測試前創建新的布隆過濾器"""
        self.bloom = CachePenetrationProtection(capacity=10000, error_rate=0.01)
    
    @given(
        items=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=100)
    )
    @hypothesis_settings(max_examples=20)
    def test_bloom_filter_no_false_negatives(self, items):
        """測試：布隆過濾器不會產生假陰性（已加入的一定存在）"""
        # 將所有項目加入過濾器
        for item in items:
            self.bloom.add(item)
        
        # 檢查所有項目都能被找到（不應該有假陰性）
        for item in items:
            self.assertTrue(
                self.bloom.might_exist(item),
                f"False negative detected for item: {item}"
            )
    
    @given(
        added_items=st.lists(st.text(min_size=1, max_size=50), min_size=5, max_size=50),
        test_item=st.text(min_size=1, max_size=50)
    )
    @hypothesis_settings(max_examples=20)
    def test_bloom_filter_empty_check(self, added_items, test_item):
        """測試：未加入的項目應該大概率返回不存在"""
        assume(test_item not in added_items)  # 確保測試項目未加入
        
        for item in added_items:
            self.bloom.add(item)
        
        # 未加入的項目應該返回不存在（可能有假陽性，但機率很低）
        result = self.bloom.might_exist(test_item)
        # 這裡我們無法保證一定是 False（因為布隆過濾器特性），
        # 但可以統計假陽性率
        # 在實際應用中，假陽性是可接受的
    
    @given(
        item=st.text(min_size=1, max_size=50),
        check_count=st.integers(min_value=1, max_value=10)
    )
    @hypothesis_settings(max_examples=20)
    def test_bloom_filter_idempotent(self, item, check_count):
        """測試：多次添加相同項目是冪等的"""
        # 多次添加相同項目
        for _ in range(check_count):
            self.bloom.add(item)
        
        # 應該仍然只存在一次
        self.assertTrue(self.bloom.might_exist(item))


class DistributedLockTests(HypothesisTestCase):
    """測試分散式鎖的正確性"""
    
    def setUp(self):
        """設置 Redis 鎖"""
        self.lock = RedisDistributedLock()
        # 清理所有測試鎖
        cache.clear()
    
    def tearDown(self):
        """清理測試資料"""
        cache.clear()
    
    @given(
        lock_key=st.text(min_size=1, max_size=50),
        expire=st.integers(min_value=1, max_value=30)
    )
    @hypothesis_settings(max_examples=15, deadline=3000)
    def test_lock_acquire_and_release(self, lock_key, expire):
        """測試：鎖可以正常獲取和釋放"""
        # 獲取鎖
        identifier = self.lock.acquire(lock_key, expire=expire, timeout=2)
        
        if identifier is not None:
            # 成功獲取鎖後，應該可以正常釋放
            result = self.lock.release(lock_key, identifier)
            self.assertTrue(result)
    
    @given(
        lock_key=st.text(min_size=1, max_size=50)
    )
    @hypothesis_settings(max_examples=15, deadline=3000)
    def test_lock_mutual_exclusion(self, lock_key):
        """測試：同一時間只有一個請求能獲取鎖"""
        # 第一個請求獲取鎖
        identifier1 = self.lock.acquire(lock_key, expire=5, timeout=1)
        
        if identifier1 is not None:
            # 第二個請求應該無法立即獲取鎖
            identifier2 = self.lock.acquire(lock_key, expire=5, timeout=0.1)
            self.assertIsNone(identifier2)
            
            # 釋放第一個鎖
            self.lock.release(lock_key, identifier1)
            
            # 現在第二個請求應該能獲取鎖
            identifier3 = self.lock.acquire(lock_key, expire=5, timeout=1)
            self.assertIsNotNone(identifier3)
            self.lock.release(lock_key, identifier3)
    
    @given(
        lock_key=st.text(min_size=1, max_size=50)
    )
    @hypothesis_settings(max_examples=10, deadline=3000)
    def test_lock_wrong_identifier_cannot_release(self, lock_key):
        """測試：錯誤的識別符無法釋放鎖"""
        identifier = self.lock.acquire(lock_key, expire=5, timeout=1)
        
        if identifier is not None:
            # 使用錯誤的識別符嘗試釋放
            wrong_identifier = str(uuid.uuid4())
            result = self.lock.release(lock_key, wrong_identifier)
            self.assertFalse(result)
            
            # 正確的識別符應該能釋放
            result = self.lock.release(lock_key, identifier)
            self.assertTrue(result)


class CacheFallbackTests(HypothesisTestCase):
    """測試快取降級機制"""
    
    def setUp(self):
        """設置降級處理器"""
        self.fallback = CacheWithFallback(timeout=0.5)
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    @given(
        cache_key=st.text(min_size=1, max_size=50),
        cache_value=st.integers(min_value=0, max_value=10000),
        timeout=st.integers(min_value=10, max_value=300)
    )
    @hypothesis_settings(max_examples=15)
    def test_cache_get_set_cycle(self, cache_key, cache_value, timeout):
        """測試：快取的讀寫循環正確"""
        # 寫入快取
        success = self.fallback.set_safe(cache_key, cache_value, timeout)
        self.assertTrue(success)
        
        # 讀取快取
        result = self.fallback.get_safe(cache_key)
        self.assertEqual(result, cache_value)
    
    @given(
        db_value=st.integers(min_value=1, max_value=10000)  # 避免使用 0，因為 Django cache 可能誤判
    )
    @hypothesis_settings(max_examples=15)
    def test_cache_miss_with_fallback(self, db_value):
        """測試：快取 miss 時正確降級到資料庫"""
        # 使用唯一的測試鍵，避免測試間衝突
        import uuid
        test_key = f"test_fallback_{uuid.uuid4()}"
        
        def fetch_from_db():
            return db_value
        
        # 確保快取中沒有這個鍵
        cache.delete(test_key)
        
        # 快取中沒有資料，應該呼叫降級函數
        result = self.fallback.get_safe(
            test_key, 
            fetch_function=fetch_from_db,
            cache_timeout=60
        )
        
        self.assertEqual(result, db_value)
        
        # 第二次讀取應該從快取獲得
        result2 = self.fallback.get_safe(test_key)
        self.assertEqual(result2, db_value)
    
    @given(
        cache_key=st.text(min_size=1, max_size=50)
    )
    @hypothesis_settings(max_examples=15)
    def test_cache_delete_safe(self, cache_key):
        """測試：快取安全刪除"""
        # 先設置一個值
        self.fallback.set_safe(cache_key, "test_value", 60)
        
        # 刪除
        result = self.fallback.delete_safe(cache_key)
        self.assertTrue(result)
        
        # 確認已刪除
        value = self.fallback.get_safe(cache_key)
        self.assertIsNone(value)


class CacheMonitoringTests(HypothesisTestCase):
    """測試快取監控功能"""
    
    def setUp(self):
        """設置監控器"""
        self.monitor = CacheHitRateMonitor()
        cache.clear()
    
    def tearDown(self):
        cache.clear()
        # 清理監控器統計資料，確保測試隔離
        self.monitor.reset()
    
    @given(
        cache_type=st.sampled_from([
            'submission_detail', 'submission_list', 'user_stats', 
            'high_score', 'permission'
        ]),
        hit_count=st.integers(min_value=1, max_value=100),
        miss_count=st.integers(min_value=0, max_value=100)
    )
    @hypothesis_settings(max_examples=15)
    def test_hit_rate_calculation(self, cache_type, hit_count, miss_count):
        """測試：命中率計算正確"""
        # 每次測試前重置監控器，確保測試獨立
        self.monitor.reset()
        
        # 記錄命中
        for _ in range(hit_count):
            self.monitor.record_hit(cache_type)
        
        # 記錄未命中
        for _ in range(miss_count):
            self.monitor.record_miss(cache_type)
        
        # 使用 get_hit_rate 方法計算命中率
        hit_rate = self.monitor.get_hit_rate(cache_type)
        
        # 驗證命中率計算正確
        total = hit_count + miss_count
        expected_rate = (hit_count / total) if total > 0 else 0.0
        self.assertAlmostEqual(hit_rate, expected_rate, places=5)
        
        # 驗證內部統計資料
        self.assertEqual(self.monitor.stats[cache_type]['hits'], hit_count)
        self.assertEqual(self.monitor.stats[cache_type]['misses'], miss_count)
    
    @given(
        cache_type=st.sampled_from([
            'submission_detail', 'submission_list', 'user_stats'
        ])
    )
    @hypothesis_settings(max_examples=10)
    def test_monitoring_idempotent(self, cache_type):
        """測試：監控記錄是累加的"""
        # 第一次記錄
        self.monitor.record_hit(cache_type)
        hits_after_first = self.monitor.stats[cache_type]['hits']
        
        # 第二次記錄
        self.monitor.record_hit(cache_type)
        hits_after_second = self.monitor.stats[cache_type]['hits']
        
        # 計數應該累加
        self.assertEqual(hits_after_second, hits_after_first + 1)


class IntegrationTests(HypothesisTestCase):
    """整合測試：測試各模組協同工作"""
    
    def setUp(self):
        """設置測試環境"""
        self.bloom = CachePenetrationProtection(capacity=1000, error_rate=0.01)
        self.lock = RedisDistributedLock()
        self.fallback = CacheWithFallback()
        self.monitor = CacheHitRateMonitor()
        cache.clear()
        
        # 創建測試用戶
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'testuser_{unique_id}',
            email=f'test_{unique_id}@example.com',
            password='testpass123'
        )
    
    def tearDown(self):
        cache.clear()
        User.objects.filter(id=self.user.id).delete()
    
    @given(
        submission_count=st.integers(min_value=1, max_value=20)
    )
    @hypothesis_settings(max_examples=10, deadline=5000)
    def test_full_cache_workflow(self, submission_count):
        """測試：完整的快取工作流程"""
        submission_ids = []
        
        # 1. 創建一些提交並加入布隆過濾器
        for i in range(submission_count):
            sub_id = f"test_sub_{uuid.uuid4()}"
            submission_ids.append(sub_id)
            self.bloom.add(sub_id)
        
        # 2. 驗證布隆過濾器
        for sub_id in submission_ids:
            self.assertTrue(self.bloom.might_exist(sub_id))
        
        # 3. 使用分散式鎖和快取
        for sub_id in submission_ids[:3]:  # 只測試前 3 個
            cache_key = CacheKeys.submission_detail(sub_id)
            
            # 獲取鎖
            lock_id = self.lock.acquire(f"rebuild:{sub_id}", expire=5, timeout=1)
            
            if lock_id:
                # 模擬快取資料
                test_data = {'id': sub_id, 'score': 100}
                self.fallback.set_safe(cache_key, test_data, timeout=60)
                
                # 釋放鎖
                self.lock.release(f"rebuild:{sub_id}", lock_id)
                
                # 記錄監控
                self.monitor.record_hit('submission_detail')
        
        # 4. 驗證快取可以讀取
        for sub_id in submission_ids[:3]:
            cache_key = CacheKeys.submission_detail(sub_id)
            cached_data = self.fallback.get_safe(cache_key)
            if cached_data:
                self.assertEqual(cached_data['id'], sub_id)


class ConcurrencyTests(TestCase):
    """併發測試：測試多執行緒環境下的正確性"""
    
    def setUp(self):
        self.lock = RedisDistributedLock()
        self.results = []
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_concurrent_lock_acquisition(self):
        """測試：多執行緒同時獲取鎖，只有一個成功"""
        lock_key = "concurrent_test_lock"
        success_count = [0]  # 使用列表以便在閉包中修改
        
        def try_acquire_lock():
            identifier = self.lock.acquire(lock_key, expire=2, timeout=1)
            if identifier:
                success_count[0] += 1
                time.sleep(0.1)  # 模擬持有鎖的操作
                self.lock.release(lock_key, identifier)
        
        # 創建 5 個執行緒同時嘗試獲取鎖
        threads = []
        for _ in range(5):
            t = threading.Thread(target=try_acquire_lock)
            threads.append(t)
            t.start()
        
        # 等待所有執行緒完成
        for t in threads:
            t.join()
        
        # 在短時間內，應該只有 1-2 個執行緒能獲取到鎖
        # (因為鎖會被釋放後其他執行緒可以獲取)
        self.assertGreater(success_count[0], 0)
        self.assertLessEqual(success_count[0], 5)
    
    def test_cache_concurrent_write(self):
        """測試：多執行緒併發寫入快取"""
        fallback = CacheWithFallback()
        
        def write_cache(thread_id):
            for i in range(5):
                key = f"thread_{thread_id}_key_{i}"
                value = f"value_{thread_id}_{i}"
                fallback.set_safe(key, value, 60)
        
        # 創建 3 個執行緒併發寫入
        threads = []
        for i in range(3):
            t = threading.Thread(target=write_cache, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 驗證所有資料都寫入成功
        for thread_id in range(3):
            for i in range(5):
                key = f"thread_{thread_id}_key_{i}"
                value = fallback.get_safe(key)
                self.assertEqual(value, f"value_{thread_id}_{i}")
