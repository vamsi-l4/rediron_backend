from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0008_alter_musclegroup_slug"),
    ]

    operations = [
        migrations.AddField(
            model_name="workouttip",
            name="featured_image",
            field=models.ImageField(blank=True, null=True, upload_to="workout_tips/"),
        ),
        migrations.AddField(
            model_name="workouttip",
            name="featured_image_url",
            field=models.URLField(blank=True, help_text="Optional remote/admin image URL"),
        ),
    ]
