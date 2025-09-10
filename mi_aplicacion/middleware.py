# mi_aplicacion/middleware.py

class DebugSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Imprime las llaves de la sesión en consola
        print(">>> SESSION KEYS:", list(request.session.keys()))
        print(">>> SESSION DATA:", dict(request.session))

        response = self.get_response(request)
        return response
