from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0006_nutritionarticle_code"),
    ]

    operations = [
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="core_concepts",
            new_name="coreConcepts",
        ),
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="why_it_matters",
            new_name="whyItMatters",
        ),
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="science_explained",
            new_name="scienceExplained",
        ),
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="practical_application",
            new_name="practicalApplication",
        ),
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="common_myths",
            new_name="commonMyths",
        ),
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="coach_insight",
            new_name="coachInsight",
        ),
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="key_takeaways",
            new_name="keyTakeaways",
        ),
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="video_title",
            new_name="videoTitle",
        ),
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="youtube_url",
            new_name="youtubeUrl",
        ),
        migrations.RenameField(
            model_name="fitnessarticle",
            old_name="related_articles",
            new_name="relatedArticles",
        ),
    ]
