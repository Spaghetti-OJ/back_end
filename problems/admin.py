from django.contrib import admin
from .models import Problem, TestCase, Tag, ProblemTag

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'difficulty', 'is_public', 'total_submissions', 'accepted_submissions', 'acceptance_rate')
    list_filter = ('difficulty', 'is_public')
    search_fields = ('title',)

@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'problem', 'case_no', 'case_group', 'weight', 'file_size')

admin.site.register(Tag)
admin.site.register(ProblemTag)
