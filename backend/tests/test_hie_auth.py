from app.hie.auth import clear_hie_token_cache

def test_hie_token_cache_clear_is_safe():
    clear_hie_token_cache()
