from django.db import migrations, models
import django.db.models.deletion


def purge_problems_without_course(apps, schema_editor):
    Problems = apps.get_model('problems', 'Problems')
    # 刪除沒有課程的題目（會連帶刪除 subtasks、test cases、tags 關聯，因為外鍵皆為 CASCADE）
    Problems.objects.filter(course_id__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
        ('problems', '0003_remove_problem_limits_and_rename_info'),
    ]

    operations = [
        migrations.RunPython(purge_problems_without_course, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='problems',
            name='course_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='courses', to='courses.courses'),
        ),
    ]
