# Generated manually for CourseGrade model

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_rename_courses_join_co_1d83b2_idx_courses_join_co_3f36cc_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseGrade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField(blank=True)),
                ('score', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grades', to='courses.courses')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='course_grades', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'course_grades',
                'ordering': ['-created_at', '-id'],
                'indexes': [
                    models.Index(fields=['course', 'student'], name='coursegrade_course_student_idx'),
                ],
            },
        ),
    ]
