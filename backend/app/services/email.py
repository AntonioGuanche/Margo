"""Email sending service via Resend API."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = "Margó <noreply@heymargo.be>"


async def send_magic_link_email(to_email: str, magic_link: str) -> bool:
    """Send a magic link login email via Resend.

    Returns True if sent successfully, False otherwise.
    Falls back to console logging in development or if no API key.
    """
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — magic link logged to console only")
        print(f"\n{'='*60}\n  MAGIC LINK: {magic_link}\n{'='*60}\n")
        return True

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
        <h1 style="color: #9a3412; font-size: 28px; margin-bottom: 8px;">Margó</h1>
        <p style="color: #78716c; font-size: 14px; margin-bottom: 32px;">Gestion des coûts alimentaires</p>

        <p style="color: #1c1917; font-size: 16px; line-height: 1.6;">
            Cliquez sur le bouton ci-dessous pour vous connecter à votre espace Margó :
        </p>

        <div style="text-align: center; margin: 32px 0;">
            <a href="{magic_link}"
               style="display: inline-block; background-color: #9a3412; color: white; font-weight: 600; font-size: 16px; padding: 14px 32px; border-radius: 8px; text-decoration: none;">
                Se connecter
            </a>
        </div>

        <p style="color: #a8a29e; font-size: 13px; line-height: 1.5;">
            Ce lien expire dans {settings.magic_link_expiry_minutes} minutes.<br>
            Si vous n'avez pas demandé ce lien, ignorez cet email.
        </p>

        <hr style="border: none; border-top: 1px solid #e7e5e4; margin: 32px 0;">
        <p style="color: #d6d3d1; font-size: 11px;">
            Margó — heymargo.be
        </p>
    </div>
    """

    payload = {
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": "Votre lien de connexion Margó",
        "html": html_content,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                RESEND_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code in (200, 201):
            logger.info(f"Magic link email sent to {to_email}")
            return True
        else:
            logger.error(
                f"Resend API error {response.status_code}: {response.text}"
            )
            # Fallback: log to console so user isn't completely blocked
            print(f"\n{'='*60}\n  MAGIC LINK (email failed): {magic_link}\n{'='*60}\n")
            return False

    except Exception as e:
        logger.error(f"Failed to send magic link email: {e}")
        print(f"\n{'='*60}\n  MAGIC LINK (exception): {magic_link}\n{'='*60}\n")
        return False
