
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
