from django.db import models

class User(models.Model):
    id_user = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        db_table = 'TBL_USER'
        managed = False

    def __str__(self):
        return self.name


class Deceased(models.Model):
    id_deceased = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    date_birth = models.DateTimeField(null=True, blank=True)
    date_death = models.DateTimeField(null=True, blank=True)
    description = models.CharField(max_length=100, null=True, blank=True)
    burial_place = models.CharField(max_length=100, null=True, blank=True)
    visualization_state = models.BooleanField(default=True)
    visualization_code = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'TBL_DECEASED'
        managed = False

    def __str__(self):
        return self.name


class Image(models.Model):
    id_image = models.BigAutoField(primary_key=True)
    image_link = models.CharField(max_length=1000)
    event_title = models.CharField(max_length=100)
    description = models.CharField(max_length=255)

    class Meta:
        db_table = 'TBL_IMAGE'
        managed = False

    def __str__(self):
        return self.event_title


class Video(models.Model):
    id_video = models.BigAutoField(primary_key=True)
    video_link = models.CharField(max_length=1000)
    event_title = models.CharField(max_length=100)
    description = models.CharField(max_length=255)

    class Meta:
        db_table = 'TBL_VIDEO'
        managed = False

    def __str__(self):
        return self.event_title
