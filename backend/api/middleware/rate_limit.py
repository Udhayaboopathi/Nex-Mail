from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

def add_rate_limiting(app):
    app.state.limiter = limiter
