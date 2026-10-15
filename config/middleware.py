from django.shortcuts import render


class AdminRosettaGuardMiddleware:
    """
    Blocks all requests to /admin/ and /rosetta/ unless the user is
    authenticated, staff, and superuser.
    No exceptions – even /admin/login/ is hidden.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith('/admin/') or path.startswith('/rosetta/'):
            user = request.user
            if not user.is_authenticated:
                return render(request, '404.html', status=404)
            if not user.is_staff:
                return render(request, '404.html', status=404)
        return self.get_response(request)



class ApiRosettaGuardMiddleware:
    """
    Blocks all requests to /api/ and /api/CreatePoem unless the user is
    authenticated, staff, and superuser.
    No exceptions – even /api/ is hidden.
    And /api/docs/ should can_api_view
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path:str = request.path 
        if path.startswith('/api/'):
            if not (
                request.user.is_authenticated
                and request.user.is_staff
                and request.user.is_superuser
            ):
                return render(request, '404.html', status=404)
        if path.startswith('/api/docs/'):
            if not (
                request.user.is_authenticated
                and request.user.can_view_api
            ):
                return render(request, '404.html', status=404)    
        return self.get_response(request)        