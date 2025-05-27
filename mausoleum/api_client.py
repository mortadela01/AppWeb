import requests

API_BASE_URL = "http://localhost:8080/api"  # Cambiar a la URL real donde corre AppServer

class APIClient:
    # def __init__(self, access_token=None):
    #     self.access_token = access_token

    # def _get_headers(self):
    #     headers = {
    #         "Content-Type": "application/json",
    #     }
    #     if self.access_token:
    #         headers["Authorization"] = f"Bearer {self.access_token}"
    #     return headers

    def __init__(self, access_token=None):
        self.access_token = access_token  # Este token debe venir del flujo de login de appWeb (Auth0)

    def set_access_token(self, token):
        self.access_token = token

    def _get_headers(self):
        headers = {
            "Content-Type": "application/json",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    # --------- USERS ---------
    def list_users(self):
        url = f"{API_BASE_URL}/users/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_user(self, user_id):
        url = f"{API_BASE_URL}/users/{user_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    # --------- DECEASED ---------
    def list_deceased(self):
        url = f"{API_BASE_URL}/deceased/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_deceased(self, deceased_id):
        url = f"{API_BASE_URL}/deceased/{deceased_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def create_deceased(self, data):
        url = f"{API_BASE_URL}/deceased/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def update_deceased(self, deceased_id, data):
        url = f"{API_BASE_URL}/deceased/{deceased_id}/"
        resp = requests.put(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def delete_deceased(self, deceased_id):
        url = f"{API_BASE_URL}/deceased/{deceased_id}/"
        resp = requests.delete(url, headers=self._get_headers())
        return resp.ok

    # --------- VIDEOS ---------
    def list_videos(self):
        url = f"{API_BASE_URL}/videos/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_video(self, video_id):
        url = f"{API_BASE_URL}/videos/{video_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def create_video(self, data):
        url = f"{API_BASE_URL}/videos/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def update_video(self, video_id, data):
        url = f"{API_BASE_URL}/videos/{video_id}/"
        resp = requests.put(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def delete_video(self, video_id):
        url = f"{API_BASE_URL}/videos/{video_id}/"
        resp = requests.delete(url, headers=self._get_headers())
        return resp.ok

    # --------- IMAGES ---------
    def list_images(self):
        url = f"{API_BASE_URL}/images/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_image(self, image_id):
        url = f"{API_BASE_URL}/images/{image_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def create_image(self, data):
        url = f"{API_BASE_URL}/images/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def update_image(self, image_id, data):
        url = f"{API_BASE_URL}/images/{image_id}/"
        resp = requests.put(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def delete_image(self, image_id):
        url = f"{API_BASE_URL}/images/{image_id}/"
        resp = requests.delete(url, headers=self._get_headers())
        return resp.ok

    # --------- RELATIONS ---------
    def list_relations(self):
        url = f"{API_BASE_URL}/relations/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_relation(self, relation_id):
        url = f"{API_BASE_URL}/relations/{relation_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def create_relation(self, data):
        url = f"{API_BASE_URL}/relations/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def update_relation(self, relation_id, data):
        url = f"{API_BASE_URL}/relations/{relation_id}/"
        resp = requests.put(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def delete_relation(self, relation_id):
        url = f"{API_BASE_URL}/relations/{relation_id}/"
        resp = requests.delete(url, headers=self._get_headers())
        return resp.ok

    # --------- USER-DECEASED ---------
    def create_user_deceased(self, data):
        url = f"{API_BASE_URL}/user-deceased/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    # --------- REQUESTS ---------
    def list_requests(self):
        url = f"{API_BASE_URL}/requests/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_request(self, request_id):
        url = f"{API_BASE_URL}/requests/{request_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def create_request(self, data):
        url = f"{API_BASE_URL}/requests/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def update_request(self, request_id, data):
        url = f"{API_BASE_URL}/requests/{request_id}/"
        resp = requests.put(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def delete_request(self, request_id):
        url = f"{API_BASE_URL}/requests/{request_id}/"
        resp = requests.delete(url, headers=self._get_headers())
        return resp.ok

    # --------- NOTIFICATIONS ---------
    def list_notifications(self):
        url = f"{API_BASE_URL}/notifications/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_notification(self, notification_id):
        url = f"{API_BASE_URL}/notifications/{notification_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def create_notification(self, data):
        url = f"{API_BASE_URL}/notifications/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def update_notification(self, notification_id, data):
        url = f"{API_BASE_URL}/notifications/{notification_id}/"
        resp = requests.put(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def delete_notification(self, notification_id):
        url = f"{API_BASE_URL}/notifications/{notification_id}/"
        resp = requests.delete(url, headers=self._get_headers())
        return resp.ok

    # --------- VR APP SPECIFIC ---------

    def get_user_id_by_qr(self, qr_code):
        url = f"{API_BASE_URL}/vr/user-id-by-qr/{qr_code}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    def get_deceased_by_user(self, user_id):
        url = f"{API_BASE_URL}/vr/deceased-by-user/{user_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_images_by_deceased(self, deceased_id):
        url = f"{API_BASE_URL}/vr/images-by-deceased/{deceased_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_videos_by_deceased(self, deceased_id):
        url = f"{API_BASE_URL}/vr/videos-by-deceased/{deceased_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    def get_relations_by_deceased(self, deceased_id):
        url = f"{API_BASE_URL}/vr/relations-by-deceased/{deceased_id}/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    # --------- APPWEB SPECIFIC ---------
    # Dashboard
    def get_dashboard(self):
        # print(f"token de acceso: {self._get_headers()}")
        url = f"{API_BASE_URL}/appweb/dashboard/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else {}

    # Family members list
    def get_family_members(self):
        print(self._get_headers())  # Para depuración, borrar después
        url = f"{API_BASE_URL}/appweb/family-members/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else {}

    # Add family member (deceased)
    def add_family_member(self, data):
        url = f"{API_BASE_URL}/appweb/family-members/add/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        print(self._get_headers()) #borrar
        return resp.json() if resp.ok else None

    # Share family member
    def share_family_member(self, id, data):
        url = f"{API_BASE_URL}/appweb/family-members/{id}/share/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    # Edit family member
    def edit_family_member(self, id, data):
        url = f"{API_BASE_URL}/appweb/family-members/{id}/edit/"
        resp = requests.put(url, json=data, headers=self._get_headers())
        return resp.json() if resp.ok else None

    # Delete family member
    def delete_family_member(self, id):
        url = f"{API_BASE_URL}/appweb/family-members/{id}/delete/"
        resp = requests.delete(url, headers=self._get_headers())
        return resp.ok

    # Request access
    def request_access(self, id_deceased):
        url = f"{API_BASE_URL}/appweb/request-access/{id_deceased}/"
        resp = requests.post(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    # Approve request
    def approve_request(self, request_id, action):
        url = f"{API_BASE_URL}/appweb/approve-request/{request_id}/{action}/"
        resp = requests.post(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    # Notifications list
    def get_notifications(self):
        url = f"{API_BASE_URL}/appweb/notifications/"
        resp = requests.get(url, headers=self._get_headers())
        return resp.json() if resp.ok else []

    # Mark notification as read
    def mark_notification_read(self, notification_id):
        url = f"{API_BASE_URL}/appweb/notifications/read/{notification_id}/"
        resp = requests.post(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    # Handle notification action (accept, decline, read)
    def handle_notification_action(self, notification_id, action):
        url = f"{API_BASE_URL}/appweb/notification-action/{notification_id}/{action}/"
        resp = requests.post(url, headers=self._get_headers())
        return resp.json() if resp.ok else None

    # --------- Search Deceased (AJAX) ---------
    def search_deceased(self, query):
        url = f"{API_BASE_URL}/deceased/search/"
        params = {"q": query}
        resp = requests.get(url, headers=self._get_headers(), params=params)
        return resp.json() if resp.ok else {"results": []}

    def get_user_by_email(self, email):
        url = f"{API_BASE_URL}/users/by-email/"
        params = {'email': email}
        resp = requests.get(url, headers=self._get_headers(), params=params)
        print(self._get_headers()) #borrar
        if resp.ok:
            return resp.json()
        return {'error': 'Request failed'}

    def create_user(self, data):
        url = f"{API_BASE_URL}/users/"
        resp = requests.post(url, json=data, headers=self._get_headers())
        if resp.ok:
            return resp.json()
        return None