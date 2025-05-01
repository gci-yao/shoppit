from paydunya import Store, Setup

def configure_paydunya():
    Setup.master_key = "4gZ4CvRz-eBuF-Wa8I-CRCy-xu9Yzf2Y5FFA"
    Setup.private_key = "test_private_85htEdDMFc4dG2Zp6EWRiOlI95L"
    Setup.public_key =  "test_public_Hzj024u675ZlO0ZFmXluty6CHOg"
    Setup.token = "cOcqaQ9HWIK6DhY1e5p2"
    Setup.mode = "test"  # ou "live"

    Store.name = "Shoppit"
    Store.tagline = "Paiement Shoppit"
