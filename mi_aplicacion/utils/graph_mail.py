import requests
from django.core.exceptions import ObjectDoesNotExist
from mi_aplicacion.models import GraphMailConfig

TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_SEND_URL = "https://graph.microsoft.com/v1.0/users/{user_email}/sendMail"


class GraphError(Exception):
    pass


def get_active_config():
    try:
        return GraphMailConfig.objects.get(activo=True)
    except ObjectDoesNotExist:
        raise GraphError("No existe una configuración activa en la base de datos.")


def get_graph_token(config):
    url = TOKEN_URL.format(tenant_id=config.tenant_id)
    payload = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "scope": config.scope,
        "grant_type": config.grant_type,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=payload, headers=headers, timeout=10)

    if resp.status_code != 200:
        raise GraphError(f"Token request failed: {resp.status_code} - {resp.text}")

    return resp.json().get("access_token")


def send_mail_graph(subject, body, content_type="Text"):
    config = get_active_config()
    token = get_graph_token(config)
    url = GRAPH_SEND_URL.format(user_email=config.email_send)

    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": content_type, "content": body},
            "toRecipients": [{"emailAddress": {"address": config.email_receive}}],
        },
        "saveToSentItems": True,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    r = requests.post(url, headers=headers, json=message, timeout=10)
    if r.status_code not in (200, 202):
        raise GraphError(f"sendMail falló: {r.status_code} - {r.text}")

    return {"status": "ok", "code": r.status_code}
