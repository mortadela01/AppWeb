# from django.db import models

# class User(models.Model):
#     id_user = models.BigAutoField(primary_key=True)
#     name = models.CharField(max_length=100)
#     email = models.CharField(max_length=100, unique=True)
#     password = models.CharField(max_length=250, blank=True, null=True)

#     class Meta:
#         db_table = 'TBL_USER'
#         managed = False

#     def __str__(self):
#         return self.name


# class Deceased(models.Model):
#     id_deceased = models.BigAutoField(primary_key=True)
#     name = models.CharField(max_length=100)
#     date_birth = models.DateTimeField(null=True, blank=True)
#     date_death = models.DateTimeField(null=True, blank=True)
#     description = models.CharField(max_length=100, null=True, blank=True)
#     burial_place = models.CharField(max_length=100, null=True, blank=True)
#     visualization_state = models.BooleanField(default=True)
#     visualization_code = models.CharField(max_length=100, null=True, blank=True)

#     class Meta:
#         db_table = 'TBL_DECEASED'
#         managed = False

#     def __str__(self):
#         return self.name


# class Image(models.Model):
#     id_image = models.BigAutoField(primary_key=True)
#     image_link = models.CharField(max_length=1000)
#     event_title = models.CharField(max_length=100)
#     description = models.CharField(max_length=255)

#     class Meta:
#         db_table = 'TBL_IMAGE'
#         managed = False

#     def __str__(self):
#         return self.event_title


# class Video(models.Model):
#     id_video = models.BigAutoField(primary_key=True)
#     video_link = models.CharField(max_length=1000)
#     event_title = models.CharField(max_length=100)
#     description = models.CharField(max_length=255)

#     class Meta:
#         db_table = 'TBL_VIDEO'
#         managed = False

#     def __str__(self):
#         return self.event_title


class User:
    def __init__(self, id_user=None, name=None, email=None, password=None):
        self.id_user = id_user
        self.name = name
        self.email = email
        self.password = password

    def __str__(self):
        return self.name or ''

class Deceased:
    def __init__(self, id_deceased=None, name=None, date_birth=None, date_death=None,
                 description=None, burial_place=None, visualization_state=None, visualization_code=None):
        self.id_deceased = id_deceased
        self.name = name
        self.date_birth = date_birth
        self.date_death = date_death
        self.description = description
        self.burial_place = burial_place
        self.visualization_state = visualization_state
        self.visualization_code = visualization_code

    def __str__(self):
        return self.name or ''

class Image:
    def __init__(self, id_image=None, image_link=None, event_title=None, description=None):
        self.id_image = id_image
        self.image_link = image_link
        self.event_title = event_title
        self.description = description

    def __str__(self):
        return self.event_title or ''

class Video:
    def __init__(self, id_video=None, video_link=None, event_title=None, description=None):
        self.id_video = id_video
        self.video_link = video_link
        self.event_title = event_title
        self.description = description

    def __str__(self):
        return self.event_title or ''
