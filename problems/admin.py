from django.contrib import admin
from .models import Problems, Test_cases, Tags, Problem_tags

@admin.register(Problems)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'difficulty', 'is_public', 'total_submissions', 'accepted_submissions', 'acceptance_rate')
    list_filter = ('difficulty', 'is_public')
    search_fields = ('title',)


@admin.register(Test_cases)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'problem_id', 'case_group', 'weight', 'file_size')
admin.site.register(Tags)
admin.site.register(Problem_tags)
