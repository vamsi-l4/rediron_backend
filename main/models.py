from django.db import models

# Create your models here.
class Equipment(models.Model):
    CATEGORY_CHOICES =[
        ('cardio','Cardio'),
        ('gym','Gym'),
        ('abs','Abs')
    ]
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='equipment_images/')
    usage = models.TextField()
    video_link = models.URLField(blank=True)
    category=models.CharField(max_length=20,choices=CATEGORY_CHOICES,default='gym')

    def __str__(self):
        return self.name
