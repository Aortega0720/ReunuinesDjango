# # mi_aplicacion/auth.py
# def oidc_username(claims):
#     return claims.get("preferred_username") or (claims.get("email") or "").split("@")[0]

# def oidc_update_user(user, claims):
#     user.email = claims.get("email", "") or user.email
#     user.first_name = claims.get("given_name", "") or user.first_name
#     user.last_name = claims.get("family_name", "") or user.last_name
#     user.save()
