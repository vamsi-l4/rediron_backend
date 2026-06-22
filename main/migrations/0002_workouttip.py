from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkoutTip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(help_text="Stable fixture ID, e.g. WT01", max_length=20, unique=True)),
                ("title", models.CharField(max_length=250)),
                ("slug", models.SlugField(blank=True, max_length=260, unique=True)),
                ("thumbnail", models.CharField(blank=True, max_length=500)),
                ("youtube_url", models.URLField(blank=True, help_text="YouTube watch URL used for embedded demo video")),
                ("category", models.CharField(choices=[("Beginner", "Beginner"), ("Form", "Form"), ("Recovery", "Recovery"), ("Strength", "Strength"), ("Advanced", "Advanced")], db_index=True, max_length=40)),
                ("overview", models.TextField(blank=True)),
                ("why_it_matters", models.JSONField(blank=True, default=list)),
                ("step_by_step_guide", models.JSONField(blank=True, default=list)),
                ("common_mistakes", models.JSONField(blank=True, default=list)),
                ("coach_tip", models.TextField(blank=True)),
                ("key_takeaways", models.JSONField(blank=True, default=list)),
                ("related_articles", models.JSONField(blank=True, default=list, help_text="List of related WorkoutTip codes")),
                ("author", models.CharField(default="RedIron Team", max_length=120)),
                ("published_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("is_published", models.BooleanField(db_index=True, default=True)),
                ("reading_time", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["category", "title"],
            },
        ),
        migrations.AddIndex(
            model_name="workouttip",
            index=models.Index(fields=["category", "is_published"], name="main_workou_categor_b43e08_idx"),
        ),
        migrations.AddIndex(
            model_name="workouttip",
            index=models.Index(fields=["slug"], name="main_workou_slug_8143c8_idx"),
        ),
    ]
