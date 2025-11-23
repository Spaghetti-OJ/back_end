# Generated manually to switch course IDs from UUID to auto-incrementing integers

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="courses",
            name="id",
            field=models.BigAutoField(
                primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="course_members",
            name="course_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="members",
                to="courses.courses",
            ),
        ),
        migrations.AlterField(
            model_name="coursegrade",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="grades",
                to="courses.courses",
            ),
        ),
        migrations.AlterField(
            model_name="announcements",
            name="course_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="announcements",
                to="courses.courses",
            ),
        ),
        migrations.AlterField(
            model_name="batch_imports",
            name="course_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="batch_imports",
                to="courses.courses",
            ),
        ),
    ]
