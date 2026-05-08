
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_remove_workoutexercise_notes_and_more'),
    ]

    operations = [
        migrations.AlterField(
             model_name='exercise',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=timezone.now),
        ),
    ]
