# Generated manually for saved checkout addresses.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0013_trial_subscription_preferences'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='recipient_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='address',
            name='phone',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
