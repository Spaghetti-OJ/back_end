"""
Django management command to seed the database with demo data.

Usage:
    python manage.py seed_data           # Seed with default data
    python manage.py seed_data --clear   # Clear existing data before seeding
    python manage.py seed_data --minimal # Seed with minimal data set
"""

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from user.models import User, UserProfile
from courses.models import Courses, Course_members, CourseGrade
from problems.models import Problems, Tags, Problem_tags, Problem_subtasks, Test_cases
from assignments.models import Assignments, Assignment_problems, Assignment_tags
from submissions.models import Submission, SubmissionResult
from editor.models import CodeDraft


class Command(BaseCommand):
    help = 'Seed the database with demo data for development and demos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )
        parser.add_argument(
            '--minimal',
            action='store_true',
            help='Seed with minimal data set',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('🌱 Starting database seeding...'))
        
        if options['clear']:
            self.clear_data()
        
        with transaction.atomic():
            if options['minimal']:
                self.seed_minimal()
            else:
                self.seed_full()
        
        self.stdout.write(self.style.SUCCESS('✅ Database seeding completed!'))

    def clear_data(self):
        """Clear existing demo data."""
        self.stdout.write(self.style.WARNING('🗑️  Clearing existing data...'))
        
        # Delete in reverse order of dependencies
        self._safe_delete(CodeDraft)
        self._safe_delete(SubmissionResult)
        self._safe_delete(Submission)
        self._safe_delete(Assignment_tags)
        self._safe_delete(Assignment_problems)
        self._safe_delete(Assignments)
        self._safe_delete(CourseGrade)
        self._safe_delete(Course_members)
        self._safe_delete(Test_cases)
        self._safe_delete(Problem_subtasks)
        self._safe_delete(Problem_tags)
        self._safe_delete(Problems)
        self._safe_delete(Tags)
        self._safe_delete(Courses)
        self._safe_delete(UserProfile)
        
        # Try to delete related auth tables that might reference User
        self._safe_delete_by_name('auths', 'EmailVerificationToken')
        self._safe_delete_by_name('auths', 'PasswordResetToken')
        
        # Keep superusers - use raw SQL to avoid cascade issues
        try:
            User.objects.filter(is_superuser=False).delete()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   Warning: Could not delete users via ORM: {e}'))
            # Fallback: delete users one by one to avoid cascade issues
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM user_user WHERE is_superuser = 0")
        
        self.stdout.write(self.style.SUCCESS('   Data cleared!'))

    def _safe_delete(self, model):
        """Safely delete all records from a model, handling missing tables."""
        try:
            model.objects.all().delete()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   Warning: Could not clear {model.__name__}: {e}'))

    def _safe_delete_by_name(self, app_name, model_name):
        """Safely delete records from a model by app and model name."""
        try:
            from django.apps import apps
            model = apps.get_model(app_name, model_name)
            model.objects.all().delete()
        except Exception:
            pass  # Table doesn't exist or model not found, skip silently

    def seed_minimal(self):
        """Seed with minimal data for quick testing."""
        admin = self.create_users(admin_only=True)
        teacher = self.create_teacher()
        students = self.create_students(count=3)
        
        course = self.create_courses(teachers=[teacher], count=1)[0]
        self.add_course_members(course, students)
        
        tags = self.create_tags()
        problems = self.create_problems(course, teacher, tags, count=3)
        
        self.stdout.write(self.style.SUCCESS('   Minimal data seeded!'))

    def seed_full(self):
        """Seed with full demo data."""
        # Create users
        admin = self.create_admin()
        teachers = self.create_teachers(count=3)
        tas = self.create_tas(count=5)
        students = self.create_students(count=20)
        
        # Create tags
        tags = self.create_tags()
        
        # Create courses with members
        courses = self.create_courses(teachers=teachers, count=5)
        for course in courses:
            # Assign random TAs and students
            course_tas = random.sample(tas, min(2, len(tas)))
            course_students = random.sample(students, min(10, len(students)))
            self.add_course_members(course, course_students, course_tas)
        
        # Create problems for each course
        all_problems = []
        for course in courses:
            teacher = course.teacher_id
            problems = self.create_problems(course, teacher, tags, count=random.randint(5, 10))
            all_problems.extend(problems)
        
        # Create assignments
        for course in courses:
            course_problems = [p for p in all_problems if p.course_id == course]
            if course_problems:
                self.create_assignments(course, course_problems, count=2)
        
        # Create submissions
        for student in students:
            self.create_submissions(student, all_problems, count=random.randint(5, 15))
        
        # Create code drafts
        for student in random.sample(students, min(10, len(students))):
            self.create_drafts(student, all_problems, count=random.randint(1, 3))
        
        # Create course grades
        for course in courses:
            self.create_course_grades(course)
        
        self.stdout.write(self.style.SUCCESS('   Full data seeded!'))

    def create_admin(self):
        """Create admin user."""
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@demo.noj.tw',
                'real_name': '系統管理員',
                'identity': User.Identity.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            UserProfile.objects.get_or_create(
                user=admin,
                defaults={'student_id': 'ADMIN001', 'email_verified': True}
            )
            self.stdout.write(f'   Created admin: {admin.username}')
        return admin

    def create_users(self, admin_only=False):
        """Create basic users."""
        return self.create_admin()

    def create_teacher(self):
        """Create a single teacher."""
        return self.create_teachers(count=1)[0]

    def create_teachers(self, count=3):
        """Create teacher users."""
        teachers = []
        teacher_data = [
            {'username': 'prof_chen', 'real_name': '陳教授', 'email': 'chen@demo.noj.tw'},
            {'username': 'prof_wang', 'real_name': '王教授', 'email': 'wang@demo.noj.tw'},
            {'username': 'prof_lin', 'real_name': '林教授', 'email': 'lin@demo.noj.tw'},
            {'username': 'prof_liu', 'real_name': '劉教授', 'email': 'liu@demo.noj.tw'},
            {'username': 'prof_zhang', 'real_name': '張教授', 'email': 'zhang@demo.noj.tw'},
        ]
        
        for i, data in enumerate(teacher_data[:count]):
            teacher, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'real_name': data['real_name'],
                    'identity': User.Identity.TEACHER,
                    'is_staff': True,
                }
            )
            if created:
                teacher.set_password('teacher123')
                teacher.save()
                UserProfile.objects.get_or_create(
                    user=teacher,
                    defaults={
                        'student_id': f'T{str(i+1).zfill(6)}',
                        'email_verified': True,
                        'bio': f'{data["real_name"]}的個人簡介'
                    }
                )
                self.stdout.write(f'   Created teacher: {teacher.username}')
            teachers.append(teacher)
        
        return teachers

    def create_tas(self, count=5):
        """Create teaching assistant users."""
        tas = []
        ta_names = ['助教小明', '助教小華', '助教小美', '助教小強', '助教小芳',
                    '助教大偉', '助教雅婷', '助教志豪']
        
        for i in range(min(count, len(ta_names))):
            username = f'ta_{i+1:02d}'
            ta, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'ta{i+1}@demo.noj.tw',
                    'real_name': ta_names[i],
                    'identity': User.Identity.STUDENT,  # TAs are students with TA role in courses
                }
            )
            if created:
                ta.set_password('ta123456')
                ta.save()
                UserProfile.objects.get_or_create(
                    user=ta,
                    defaults={
                        'student_id': f'TA{str(i+1).zfill(6)}',
                        'email_verified': True,
                        'bio': f'我是{ta_names[i]}，負責課程助教工作'
                    }
                )
                self.stdout.write(f'   Created TA: {ta.username}')
            tas.append(ta)
        
        return tas

    def create_students(self, count=20):
        """Create student users."""
        students = []
        first_names = ['小明', '小華', '小美', '小強', '小芳', '大偉', '雅婷', '志豪',
                       '怡君', '俊傑', '佳琪', '承翰', '詩涵', '宗翰', '欣怡', '冠廷',
                       '雅文', '柏翰', '筱婷', '宇軒', '思妤', '子傑', '品萱', '彥廷']
        last_names = ['王', '李', '張', '劉', '陳', '楊', '黃', '趙', '周', '吳',
                      '徐', '孫', '馬', '朱', '胡', '郭', '何', '高', '林', '羅']
        
        for i in range(count):
            first = random.choice(first_names)
            last = random.choice(last_names)
            username = f'student_{i+1:03d}'
            
            student, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'student{i+1}@demo.noj.tw',
                    'real_name': f'{last}{first}',
                    'identity': User.Identity.STUDENT,
                }
            )
            if created:
                student.set_password('student123')
                student.save()
                UserProfile.objects.get_or_create(
                    user=student,
                    defaults={
                        'student_id': f'B{111000000 + i}',
                        'email_verified': random.choice([True, True, True, False]),  # 75% verified
                        'bio': random.choice(['', '', '熱愛程式設計！', '正在學習中...', '資工系學生'])
                    }
                )
                self.stdout.write(f'   Created student: {student.username}')
            students.append(student)
        
        return students

    def create_tags(self):
        """Create problem tags."""
        tag_names = [
            'Array', 'String', 'Sorting', 'Binary Search', 'Dynamic Programming',
            'Greedy', 'Graph', 'BFS', 'DFS', 'Tree', 'Recursion', 'Stack',
            'Queue', 'Hash Table', 'Two Pointers', 'Linked List', 'Math',
            'Bit Manipulation', 'Backtracking', 'Simulation'
        ]
        
        tags = []
        for name in tag_names:
            tag, created = Tags.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f'   Created tag: {name}')
            tags.append(tag)
        
        return tags

    def create_courses(self, teachers, count=5):
        """Create courses."""
        courses = []
        course_data = [
            {
                'name': '程式設計（一）',
                'description': '本課程介紹程式設計的基本概念，包括變數、運算子、流程控制、函式等。適合初學者入門。',
                'semester': '上學期',
                'academic_year': '113',
            },
            {
                'name': '程式設計（二）',
                'description': '延續程式設計（一），深入探討資料結構、演算法基礎、物件導向程式設計等進階概念。',
                'semester': '下學期',
                'academic_year': '113',
            },
            {
                'name': '資料結構',
                'description': '學習各種資料結構：陣列、鏈結串列、堆疊、佇列、樹、圖等，及其應用與演算法分析。',
                'semester': '上學期',
                'academic_year': '113',
            },
            {
                'name': '演算法概論',
                'description': '介紹演算法設計與分析技巧，包括分治法、動態規劃、貪婪法、圖論演算法等。',
                'semester': '下學期',
                'academic_year': '113',
            },
            {
                'name': '競技程式設計',
                'description': '針對程式競賽的進階訓練課程，涵蓋各種經典題型與解題技巧。',
                'semester': '全年',
                'academic_year': '113',
            },
            {
                'name': 'Python 程式設計',
                'description': '使用 Python 學習程式設計，涵蓋基礎語法、資料處理、網路爬蟲等實用技能。',
                'semester': '上學期',
                'academic_year': '114',
            },
        ]
        
        for i, data in enumerate(course_data[:count]):
            teacher = teachers[i % len(teachers)]
            course, created = Courses.objects.get_or_create(
                name=data['name'],
                academic_year=data['academic_year'],
                semester=data['semester'],
                defaults={
                    'description': data['description'],
                    'teacher_id': teacher,
                    'is_active': True,
                    'student_limit': random.choice([30, 40, 50, 60, None]),
                }
            )
            if created:
                # Add teacher as course member
                Course_members.objects.create(
                    course_id=course,
                    user_id=teacher,
                    role=Course_members.Role.TEACHER
                )
                self.stdout.write(f'   Created course: {course.name}')
            courses.append(course)
        
        return courses

    def add_course_members(self, course, students, tas=None):
        """Add members to a course."""
        if tas:
            for ta in tas:
                Course_members.objects.get_or_create(
                    course_id=course,
                    user_id=ta,
                    defaults={'role': Course_members.Role.TA}
                )
        
        for student in students:
            Course_members.objects.get_or_create(
                course_id=course,
                user_id=student,
                defaults={'role': Course_members.Role.STUDENT}
            )
        
        # Update student count
        course.student_count = course.members.filter(role=Course_members.Role.STUDENT).count()
        course.save(update_fields=['student_count'])

    def create_problems(self, course, teacher, tags, count=5):
        """Create problems for a course."""
        problems = []
        problem_templates = [
            {
                'title': 'Hello World',
                'difficulty': Problems.Difficulty.EASY,
                'description': '# 題目說明\n\n請寫一個程式，輸出 "Hello, World!"。\n\n## 輸入格式\n\n無輸入。\n\n## 輸出格式\n\n輸出一行 `Hello, World!`',
                'sample_input': '',
                'sample_output': 'Hello, World!',
                'hint': '這是最基礎的程式題目，只需要使用輸出函式即可。',
                'tags': ['String'],
            },
            {
                'title': '兩數之和',
                'difficulty': Problems.Difficulty.EASY,
                'description': '# 題目說明\n\n給定兩個整數 a 和 b，請計算並輸出它們的和。\n\n## 輸入格式\n\n一行，包含兩個整數 a 和 b，以空格分隔。\n\n## 輸出格式\n\n輸出一行，為 a + b 的結果。',
                'sample_input': '3 5',
                'sample_output': '8',
                'hint': '注意資料型態和輸入格式。',
                'tags': ['Math'],
            },
            {
                'title': '最大值',
                'difficulty': Problems.Difficulty.EASY,
                'description': '# 題目說明\n\n給定 N 個整數，請找出其中的最大值。\n\n## 輸入格式\n\n第一行包含一個整數 N。\n第二行包含 N 個整數，以空格分隔。\n\n## 輸出格式\n\n輸出最大的整數。',
                'sample_input': '5\n3 1 4 1 5',
                'sample_output': '5',
                'hint': '可以使用迴圈逐一比較，或使用內建函式。',
                'tags': ['Array'],
            },
            {
                'title': '費氏數列',
                'difficulty': Problems.Difficulty.MEDIUM,
                'description': '# 題目說明\n\n費氏數列定義為：F(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2)。\n給定 N，請輸出 F(N)。\n\n## 輸入格式\n\n一個整數 N (0 ≤ N ≤ 40)。\n\n## 輸出格式\n\n輸出 F(N) 的值。',
                'sample_input': '10',
                'sample_output': '55',
                'hint': '可以使用遞迴或迴圈，注意效能問題。',
                'tags': ['Recursion', 'Dynamic Programming'],
            },
            {
                'title': '二分搜尋',
                'difficulty': Problems.Difficulty.MEDIUM,
                'description': '# 題目說明\n\n給定一個已排序的整數陣列和目標值，請找出目標值在陣列中的索引。如果目標值不存在，回傳 -1。\n\n## 輸入格式\n\n第一行包含兩個整數 N 和 T。\n第二行包含 N 個已排序的整數。\n\n## 輸出格式\n\n輸出目標值的索引（0-based），或 -1。',
                'sample_input': '5 4\n1 2 3 4 5',
                'sample_output': '3',
                'hint': '二分搜尋的時間複雜度為 O(log N)。',
                'tags': ['Binary Search', 'Array'],
            },
            {
                'title': '泡沫排序',
                'difficulty': Problems.Difficulty.MEDIUM,
                'description': '# 題目說明\n\n請實作泡沫排序法，將給定的整數陣列由小到大排序。\n\n## 輸入格式\n\n第一行包含一個整數 N。\n第二行包含 N 個整數。\n\n## 輸出格式\n\n輸出排序後的結果，以空格分隔。',
                'sample_input': '5\n5 2 8 1 9',
                'sample_output': '1 2 5 8 9',
                'hint': '泡沫排序的時間複雜度為 O(N²)。',
                'tags': ['Sorting', 'Array'],
            },
            {
                'title': '字串反轉',
                'difficulty': Problems.Difficulty.EASY,
                'description': '# 題目說明\n\n給定一個字串，請輸出反轉後的結果。\n\n## 輸入格式\n\n一行字串，長度不超過 1000。\n\n## 輸出格式\n\n輸出反轉後的字串。',
                'sample_input': 'hello',
                'sample_output': 'olleh',
                'hint': '可以使用迴圈或內建函式。',
                'tags': ['String'],
            },
            {
                'title': '迷宮路徑',
                'difficulty': Problems.Difficulty.HARD,
                'description': '# 題目說明\n\n給定一個 N×M 的迷宮，0 表示可通行，1 表示障礙。請找出從左上角到右下角的最短路徑長度。\n\n## 輸入格式\n\n第一行包含兩個整數 N 和 M。\n接下來 N 行，每行包含 M 個整數。\n\n## 輸出格式\n\n輸出最短路徑長度，若無法到達則輸出 -1。',
                'sample_input': '3 3\n0 0 0\n1 1 0\n0 0 0',
                'sample_output': '4',
                'hint': '使用 BFS 來找最短路徑。',
                'tags': ['BFS', 'Graph'],
            },
            {
                'title': '最長共同子序列',
                'difficulty': Problems.Difficulty.HARD,
                'description': '# 題目說明\n\n給定兩個字串，請找出它們的最長共同子序列長度。\n\n## 輸入格式\n\n兩行，分別為兩個字串。\n\n## 輸出格式\n\n輸出最長共同子序列的長度。',
                'sample_input': 'ABCDGH\nAEDFHR',
                'sample_output': '3',
                'hint': '經典的動態規劃問題，使用二維 DP 表格。',
                'tags': ['Dynamic Programming', 'String'],
            },
            {
                'title': '括號匹配',
                'difficulty': Problems.Difficulty.MEDIUM,
                'description': '# 題目說明\n\n給定一個只包含 ()[]{}的字串，判斷括號是否正確匹配。\n\n## 輸入格式\n\n一行字串。\n\n## 輸出格式\n\n如果匹配正確，輸出 Yes；否則輸出 No。',
                'sample_input': '({[]})',
                'sample_output': 'Yes',
                'hint': '使用堆疊來解決這個問題。',
                'tags': ['Stack', 'String'],
            },
        ]
        
        selected = random.sample(problem_templates, min(count, len(problem_templates)))
        
        for template in selected:
            problem = Problems.objects.create(
                title=template['title'],
                difficulty=template['difficulty'],
                description=template['description'],
                sample_input=template['sample_input'],
                sample_output=template['sample_output'],
                hint=template.get('hint', ''),
                creator_id=teacher,
                course_id=course,
                is_public=random.choice([
                    Problems.Visibility.PUBLIC,
                    Problems.Visibility.COURSE,
                    Problems.Visibility.HIDDEN,
                ]),
                max_score=100,
                total_submissions=random.randint(0, 100),
                accepted_submissions=0,  # Will be calculated
            )
            
            # Set accepted submissions (should be <= total)
            problem.accepted_submissions = random.randint(0, problem.total_submissions)
            problem.recompute_acceptance_rate(save=True)
            
            # Add tags
            for tag_name in template.get('tags', []):
                tag = next((t for t in tags if t.name == tag_name), None)
                if tag:
                    Problem_tags.objects.create(problem_id=problem, tag_id=tag, added_by=teacher)
                    tag.usage_count += 1
                    tag.save()
            
            # Create subtasks and test cases
            self.create_subtasks_and_testcases(problem)
            
            self.stdout.write(f'   Created problem: {problem.title}')
            problems.append(problem)
        
        return problems

    def create_subtasks_and_testcases(self, problem):
        """Create subtasks and test cases for a problem."""
        num_subtasks = random.randint(1, 3)
        
        for subtask_no in range(1, num_subtasks + 1):
            subtask = Problem_subtasks.objects.create(
                problem_id=problem,
                subtask_no=subtask_no,
                weight=100 // num_subtasks,
                time_limit_ms=random.choice([1000, 2000, 3000]),
                memory_limit_mb=random.choice([256, 512]),
            )
            
            # Create test cases for this subtask
            num_testcases = random.randint(2, 5)
            for idx in range(1, num_testcases + 1):
                Test_cases.objects.create(
                    subtask_id=subtask,
                    idx=idx,
                    input_path=f'testcases/{problem.id}/{subtask_no}/{idx}.in',
                    output_path=f'testcases/{problem.id}/{subtask_no}/{idx}.out',
                    input_size=random.randint(10, 1000),
                    output_size=random.randint(1, 100),
                    status='draft',
                )

    def create_assignments(self, course, problems, count=2):
        """Create assignments for a course."""
        now = timezone.now()
        
        assignment_titles = [
            '第一週作業：基礎練習',
            '第二週作業：流程控制',
            '第三週作業：函式練習',
            '期中考練習題',
            '進階挑戰題',
            '期末專題作業',
        ]
        
        assignments = []
        for i in range(count):
            start = now - timedelta(days=random.randint(0, 30))
            due = start + timedelta(days=random.randint(7, 14))
            
            assignment = Assignments.objects.create(
                title=assignment_titles[i % len(assignment_titles)],
                description=f'這是課程「{course.name}」的作業，請在期限內完成。',
                course=course,
                creator=course.teacher_id,
                start_time=start,
                due_time=due,
                late_penalty=random.choice([Decimal('0'), Decimal('10'), Decimal('20')]),
                max_attempts=-1,
                visibility=Assignments.Visibility.COURSE_ONLY,
                status=random.choice([Assignments.Status.ACTIVE, Assignments.Status.DRAFT]),
            )
            
            # Add problems to assignment
            selected_problems = random.sample(problems, min(3, len(problems)))
            for order, prob in enumerate(selected_problems, 1):
                Assignment_problems.objects.create(
                    assignment=assignment,
                    problem=prob,
                    order_index=order,
                    weight=Decimal('1.00'),
                    partial_score=True,
                )
            
            self.stdout.write(f'   Created assignment: {assignment.title}')
            assignments.append(assignment)
        
        return assignments

    def create_submissions(self, student, problems, count=10):
        """Create submissions for a student."""
        code_samples = {
            0: '''#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}''',
            1: '''#include <iostream>
using namespace std;

int main() {
    int a, b;
    cin >> a >> b;
    cout << a + b << endl;
    return 0;
}''',
            2: '''def main():
    n = int(input())
    nums = list(map(int, input().split()))
    print(max(nums))

if __name__ == "__main__":
    main()''',
            3: '''import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        System.out.println(n * 2);
    }
}''',
        }
        
        status_weights = [
            ('0', 40),   # Accepted - 40%
            ('1', 25),   # Wrong Answer - 25%
            ('-1', 10),  # Pending - 10%
            ('3', 10),   # TLE - 10%
            ('5', 10),   # Runtime Error - 10%
            ('2', 5),    # Compilation Error - 5%
        ]
        
        submissions = []
        selected_problems = random.sample(problems, min(count, len(problems)))
        
        for problem in selected_problems:
            lang = random.randint(0, 3)
            code = code_samples.get(lang, code_samples[2])
            
            status = random.choices(
                [s[0] for s in status_weights],
                weights=[s[1] for s in status_weights],
                k=1
            )[0]
            
            score = 0
            if status == '0':  # Accepted
                score = problem.max_score
            elif status == '1':  # Wrong Answer
                score = random.randint(0, problem.max_score - 1)
            
            submission = Submission.objects.create(
                problem_id=problem.id,
                user=student,
                language_type=lang,
                source_code=code,
                status=status,
                score=score,
                max_score=problem.max_score,
                execution_time=random.randint(10, 2000) if status != '-1' else -1,
                memory_usage=random.randint(1000, 50000) if status != '-1' else -1,
                is_late=random.random() < 0.1,  # 10% chance of being late
                attempt_number=random.randint(1, 5),
            )
            
            # Update problem statistics
            problem.total_submissions += 1
            if status == '0':
                problem.accepted_submissions += 1
            problem.recompute_acceptance_rate(save=True)
            
            submissions.append(submission)
        
        return submissions

    def create_drafts(self, student, problems, count=2):
        """Create code drafts for a student."""
        drafts = []
        selected = random.sample(problems, min(count, len(problems)))
        
        for problem in selected:
            lang = random.randint(0, 3)
            draft = CodeDraft.objects.create(
                user=student,
                problem_id=problem.id,
                language_type=lang,
                source_code=f'# Draft for problem {problem.id}\n# Work in progress...\n',
                auto_saved=random.choice([True, False]),
            )
            drafts.append(draft)
        
        return drafts

    def create_course_grades(self, course):
        """Create course grades for students."""
        students = Course_members.objects.filter(
            course_id=course,
            role=Course_members.Role.STUDENT
        ).values_list('user_id', flat=True)
        
        for student_id in students[:5]:  # Only create for some students
            student = User.objects.get(pk=student_id)
            CourseGrade.objects.create(
                course=course,
                student=student,
                title='期中成績',
                content='包含作業和小考成績',
                score={
                    'homework': random.randint(60, 100),
                    'quiz': random.randint(50, 100),
                    'midterm': random.randint(40, 100),
                    'total': random.randint(50, 100),
                }
            )
