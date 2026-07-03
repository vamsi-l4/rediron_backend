from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_address_fitnessprogress_gymsubscription_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='profile_image_data',
            field=models.TextField(blank=True, help_text='Permanent data URL copy of the current profile picture'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='profile_image_mime',
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
