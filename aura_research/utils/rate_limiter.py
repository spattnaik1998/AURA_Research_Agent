"""
Shared rate limiter configuration for AURA
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create a shared limiter instance that all routes can use
limiter = Limiter(key_func=get_remote_address)
