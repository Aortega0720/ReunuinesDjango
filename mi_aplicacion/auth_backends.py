from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import User

class CustomOIDCBackend(OIDCAuthenticationBackend):
    def create_user(self, claims):
        """Crear un usuario nuevo a partir de los claims de Keycloak."""
        user = super().create_user(claims)
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.email = claims.get("email", "")
        user.save()
        return user

    def update_user(self, user, claims):
        """Actualizar usuario existente cada vez que entra."""
        user.first_name = claims.get("given_name", user.first_name)
        user.last_name = claims.get("family_name", user.last_name)
        user.email = claims.get("email", user.email)
        user.save()
        return user

    def get_userinfo(self, access_token, id_token, payload):
        """Guardar el id_token en la sesión para poder cerrar sesión globalmente."""
        userinfo = super().get_userinfo(access_token, id_token, payload)

        if self.request:  # aseguramos que haya request
            self.request.session["oidc_id_token"] = id_token

        return userinfo
