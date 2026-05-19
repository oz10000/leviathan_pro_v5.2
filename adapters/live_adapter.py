from adapters.testnet_adapter import TestnetAdapter

class LiveAdapter(TestnetAdapter):
    def __init__(self, api_key, secret_key, passphrase, symbols):
        super().__init__(api_key, secret_key, passphrase, symbols)
        # Override client for live
        from app_streamlit.okx_client import OKXClient
        self.client = OKXClient(api_key, secret_key, passphrase, testnet=False)
