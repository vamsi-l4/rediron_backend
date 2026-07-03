from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_userprofile_profile_image_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="trialsubscription",
            name="renewal_preference",
            field=models.CharField(
                choices=[
                    ("auto", "Auto-renew after trial"),
                    ("manual", "Manual renewal only"),
                ],
                default="manual",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="trialsubscription",
            name="subscription_status",
            field=models.CharField(default="trial_active", max_length=20, db_index=True),
        ),
        migrations.AddField(
            model_name="trialsubscription",
            name="trial_used",
            field=models.BooleanField(default=True),
        ),
    ]
