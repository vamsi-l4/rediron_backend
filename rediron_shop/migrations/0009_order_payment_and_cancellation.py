from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rediron_shop', '0008_repair_shop_sequences'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(blank=True, default='cod', max_length=40),
        ),
        migrations.AddField(
            model_name='order',
            name='cancellation_reason',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='order',
            name='cancellation_notes',
            field=models.TextField(blank=True),
        ),
    ]
