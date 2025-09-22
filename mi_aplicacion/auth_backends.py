# mi_aplicacion/auth_backends.py
import logging
from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.utils import timezone

logger = logging.getLogger("mi_aplicacion.auth_backend")
User = get_user_model()

class CustomOIDCBackend(OIDCAuthenticationBackend):
    """
    Backend OIDC que:
    - busca por keycloak_id (sub) en KeycloakProfile
    - crea usuario si no existe (guardando keycloak_id en KeycloakProfile)
    - actualiza datos básicos
    - guarda id_token en DB (no solo sesión)
    """

    def filter_users_by_claims(self, claims):
        """Primero intenta por 'sub' (keycloak id) luego por email."""
        from mi_aplicacion.models import KeycloakProfile

        sub = claims.get("sub")
        if sub:
            try:
                profile = KeycloakProfile.objects.get(keycloak_id=sub)
                logger.debug("filter_users_by_claims: encontrado perfil por sub=%s -> user=%s", sub, profile.user_id)
                return User.objects.filter(pk=profile.user_id)
            except KeycloakProfile.DoesNotExist:
                logger.debug("filter_users_by_claims: no existe perfil para sub=%s", sub)

        email = claims.get("email")
        if email:
            logger.debug("filter_users_by_claims: buscando por email=%s", email)
            return User.objects.filter(email__iexact=email)

        return User.objects.none()

    def create_user(self, claims):
        """Crear usuario y crear KeycloakProfile con keycloak_id."""
        from mi_aplicacion.models import KeycloakProfile

        logger.info("create_user: claims recibidos: email=%s sub=%s",
                    claims.get("email"), claims.get("sub"))

        user = super().create_user(claims)  # mozilla crea username/email
        # actualizar campos
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.email = claims.get("email", user.email or "")
        user.save()

        sub = claims.get("sub")
        if sub:
            # crea o actualiza perfil
            profile, created = KeycloakProfile.objects.get_or_create(user=user, defaults={"keycloak_id": sub})
            if not created and profile.keycloak_id != sub:
                profile.keycloak_id = sub
                profile.save(update_fields=["keycloak_id", "updated_at"])
            logger.info("create_user: perfil Keycloak %s para user=%s", ("creado" if created else "actualizado"), user.id)
        else:
            logger.warning("create_user: claims no tiene 'sub' — no se creó KeycloakProfile")

        return user

    def update_user(self, user, claims):
        """Actualizar datos básicos y asegurar perfil keycloak."""
        from mi_aplicacion.models import KeycloakProfile

        logger.debug("update_user: user=%s claims=%s", getattr(user, "id", None), {"sub": claims.get("sub")})
        user.first_name = claims.get("given_name", user.first_name)
        user.last_name = claims.get("family_name", user.last_name)
        user.email = claims.get("email", user.email)
        user.save()

        sub = claims.get("sub")
        if sub:
            profile, created = KeycloakProfile.objects.get_or_create(user=user, defaults={"keycloak_id": sub})
            if not created and profile.keycloak_id != sub:
                profile.keycloak_id = sub
                profile.save(update_fields=["keycloak_id", "updated_at"])

        return user

    def get_userinfo(self, access_token, id_token, payload):
        """
        Guarda id_token de forma persistente (KeycloakProfile) y también en session
        para cerrar sesión globalmente si se requiere.
        """
        userinfo = super().get_userinfo(access_token, id_token, payload)

        try:
            request = getattr(self, "request", None)
            # si tenemos request, guardamos en session (fallback)
            if request:
                request.session["oidc_id_token"] = id_token

            # intentar persistir en DB si hay user autenticado en this flow
            sub = payload.get("sub") or userinfo.get("sub")
            # no siempre tenemos user aquí, pero intentamos mapear por sub
            if sub:
                from mi_aplicacion.models import KeycloakProfile
                try:
                    profile = KeycloakProfile.objects.get(keycloak_id=sub)
                    profile.id_token = id_token
                    profile.updated_at = timezone.now()
                    profile.save(update_fields=["id_token", "updated_at"])
                    logger.debug("get_userinfo: id_token guardado en DB para sub=%s", sub)
                except KeycloakProfile.DoesNotExist:
                    # no existe perfil todavía — se creará en create_user/update_user
                    logger.debug("get_userinfo: no hay KeycloakProfile para sub=%s (aún)", sub)
        except Exception:
            logger.exception("get_userinfo: error guardando id_token en DB")

        return userinfo
