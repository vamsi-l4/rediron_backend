from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_alter_equipment_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipment',
            name='key_features',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='equipment',
            name='specifications',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='equipment',
            name='benefits',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='equipment',
            name='perfect_for',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='equipment',
            name='additional_stats',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
