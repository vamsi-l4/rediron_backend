from django.db import migrations, models
import django.db.models.deletion


MUSCLE_TREE = {
    "Chest": ["Upper Chest", "Middle Chest", "Lower Chest"],
    "Back": ["Lats", "Mid Back", "Traps", "Erector Spinae"],
    "Shoulders": ["Front Delts", "Side Delts", "Rear Delts"],
    "Legs": ["Quads", "Hamstrings", "Glutes", "Calves"],
    "Biceps": ["Long Head", "Short Head", "Brachialis"],
    "Triceps": ["Long Head", "Lateral Head", "Medial Head"],
    "Forearms": ["Brachioradialis", "Wrist Flexors", "Wrist Extensors"],
    "Abs": ["Upper Abs", "Lower Abs", "Obliques", "Static Core"],
    "Cardio": ["Treadmill", "Cycling", "Rowing", "HIIT", "Jump Rope", "Stair Climber"],
}


def rebuild_muscle_groups(apps, schema_editor):
    MuscleGroup = apps.get_model("main", "MuscleGroup")
    db_alias = schema_editor.connection.alias

    # Ensure we always start from a clean state for this rebuild.
    MuscleGroup.objects.using(db_alias).all().delete()

    for parent_name, children in MUSCLE_TREE.items():

        # NOTE: This migration may run before `body_region` is added to the historical
        # state of MuscleGroup. Only pass it if the field exists.
        musclegroup_fields = {f.name for f in MuscleGroup._meta.get_fields()}
        has_body_region = "body_region" in musclegroup_fields

        create_kwargs_parent = {
            "name": parent_name,
            "slug": parent_name.lower().replace(" ", "-"),
        }
        if has_body_region:
            create_kwargs_parent["body_region"] = parent_name.lower()

        # Avoid failing if the parent muscle group already exists.
        parent, _ = MuscleGroup.objects.using(db_alias).get_or_create(**create_kwargs_parent)


        for child_name in children:
            create_kwargs_child = {
                "name": child_name,
                "slug": f"{parent.slug}-{child_name.lower().replace(' ', '-')}",
            }
            # NOTE: depending on the historical state of MuscleGroup at this migration,
            # the `parent` FK might not exist yet.
            if "parent" in musclegroup_fields:
                create_kwargs_child["parent"] = parent

            if has_body_region:
                create_kwargs_child["body_region"] = parent.body_region

            # Use get_or_create for children. This is robust because at this point in history,
            # the `name` field is unique. This will correctly create the first "Long Head"
            # and then simply retrieve it on subsequent attempts, avoiding the IntegrityError.
            MuscleGroup.objects.using(db_alias).get_or_create(name=child_name, defaults=create_kwargs_child)






class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_fitnessarticle_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="exercise",
            name="benefits",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="exercise",
            name="code",
            field=models.CharField(blank=True, help_text="Stable exercise code, e.g. LG-CV-04", max_length=30, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="exercise",
            name="common_mistakes",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="exercise",
            name="featured_image_url",
            field=models.URLField(blank=True, help_text="Optional remote/admin URL fallback for featured image"),
        ),
        migrations.AddField(
            model_name="exercise",
            name="how_to_perform",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="exercise",
            name="muscle_group",
            field=models.CharField(choices=[("Chest", "Chest"), ("Back", "Back"), ("Shoulders", "Shoulders"), ("Legs", "Legs"), ("Biceps", "Biceps"), ("Triceps", "Triceps"), ("Forearms", "Forearms"), ("Abs", "Abs"), ("Cardio", "Cardio")], db_index=True, default="Chest", max_length=30),
        ),
        migrations.AddField(
            model_name="exercise",
            name="related_exercises",
            field=models.JSONField(blank=True, default=list, help_text="List of related Exercise codes or slugs"),
        ),
        migrations.AddField(
            model_name="exercise",
            name="sample_30_day_challenge",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="exercise",
            name="subcategory",
            field=models.CharField(blank=True, db_index=True, max_length=80),
        ),
        migrations.AddField(
            model_name="exercise",
            name="tips",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="exercise",
            name="variations",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="exercise",
            name="youtube_url",
            field=models.URLField(blank=True, help_text="YouTube embed/watch URL for the demonstration video"),
        ),
        migrations.AlterField(
            model_name="exercise",
            name="exercise_type",
            field=models.CharField(choices=[("strength", "Strength"), ("hypertrophy", "Hypertrophy"), ("cardio", "Cardio"), ("mobility", "Mobility"), ("functional", "Functional"), ("isolation", "Isolation")], default="strength", max_length=20),
        ),
        migrations.DeleteModel(
            name="WorkoutExercise",
        ),
        migrations.DeleteModel(
            name="Workout",
        ),
        migrations.RunPython(rebuild_muscle_groups, migrations.RunPython.noop),
    ]
