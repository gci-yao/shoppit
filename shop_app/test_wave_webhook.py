import requests
import json

# URL de ton endpoint local (si tu utilises ngrok, remplace par l'URL ngrok)
WEBHOOK_URL = "http://localhost:8000/wave/webhook/"  # ou https://xxxxxxxx.ngrok.io/wave/webhook/

# Simulation des données que Wave enverrait
payload = {
    "phone_number": "+2250700000000",
    "amount": "7000.00",  # total attendu (produits + frais de livraison)
    "reference": "ABCD1234",  # doit correspondre au cart_code existant
    "status": "completed"
}

# Simuler un POST
response = requests.post(
    WEBHOOK_URL,
    data=json.dumps(payload),
    headers={"Content-Type": "application/json"}
)

# Résultat
print("Statut:", response.status_code)
print("Réponse:", response.json())
