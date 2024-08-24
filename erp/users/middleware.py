from .models import CustomUser

class UserIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the user's IP address from the request
        user_ip = request.META.get('REMOTE_ADDR')
        # Save or update the user's IP address in the CustomUser model
        if request.user.is_authenticated and not request.user.is_superuser:
            myuser = CustomUser.objects.get(username = request.user.username)
            myuser.adresse_ip = user_ip
            myuser.save()

        response = self.get_response(request)
        return response