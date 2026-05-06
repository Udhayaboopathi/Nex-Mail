from aiosmtpd.controller import Controller
from backend.smtp.handler import InboundHandler, SubmissionHandler
import ssl

async def create_smtp_servers():
    tls_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    tls_ctx.load_cert_chain("/etc/ssl/mail/fullchain.pem", "/etc/ssl/mail/privkey.pem")
    c1 = Controller(InboundHandler(), hostname='0.0.0.0', port=25)
    c2 = Controller(
        SubmissionHandler(),
        hostname='0.0.0.0',
        port=587,
        require_starttls=True,
        tls_context=tls_ctx,
        auth_require_tls=True,
    )
    c1.start()
    c2.start()
    return c1, c2
