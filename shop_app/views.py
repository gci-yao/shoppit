from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from .models import Product, Cart, CartItem, Transaction
from .serializers import ProductSerializer, DetaileProductSerializer, CartItemSerializer, SimpleCartSerializer, CartSerializer, UserSerializer
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse, JsonResponse, FileResponse
from django.core.mail import send_mail
import logging

# payment 

from django.views.decorators.csrf import csrf_exempt

import json
from django.core.mail import EmailMessage
from io import BytesIO
from reportlab.pdfgen import canvas
from django.conf import settings
from decimal import Decimal
from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa  # pip install xhtml2pdf
import uuid
import requests
from django.template.loader import get_template

import io

import paypalrestsdk

BASE_URL = settings.REACT_BASE_URL

logger = logging.getLogger(__name__)

paypalrestsdk.configure({
    "mode":settings.PAYPAL_MODE,
    "client_id":settings.PAYPAL_CLIENT_ID,
    "client_secret":settings.PAYPAL_CLIENT_SECRET
})


def generate_invoice_pdf(cart):
    template = get_template('invoice_template.html')

    # Calcul du total du panier
    total = sum(item.product.price * item.quantity for item in cart.items.all())

    html = template.render({'cart': cart, 'total': total})
    result = io.BytesIO()
    pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    return result

def test_pdf(request):
    cart = Cart.objects.get(cart_code="TEST1234")
    pdf = generate_invoice_pdf(cart)
    
    return HttpResponse(pdf.getvalue(), content_type='application/pdf')



@csrf_exempt
def wave_webhook(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            cart_code = data.get("cart_code")  # Transmis via motif de paiement
            amount = Decimal(str(data.get("amount")))
            status = data.get("status")
            ref = data.get("ref")  # Référence de paiement unique

            if not all([cart_code, amount, status, ref]):
                return JsonResponse({"error": "Champs manquants"}, status=400)

            try:
                cart = Cart.objects.get(cart_code=cart_code)
            except Cart.DoesNotExist:
                return JsonResponse({"error": "Panier non trouvé"}, status=404)

            total_cart_amount = sum(item.product.price * item.quantity for item in cart.items.all())

            if amount != total_cart_amount:
                # Email admin si le montant est incorrect
                send_mail(
                    subject="Paiement Wave incorrect",
                    message=f"Un utilisateur a payé {amount} au lieu de {total_cart_amount} pour le panier {cart_code}.",
                    from_email="charlesyao1602@gmail.com",
                    recipient_list=["charlesyao1602@gmail.com"],
                )
                return JsonResponse({"message": "Montant incorrect. Paiement signalé."}, status=400)

            # Montant OK → marquer comme payé
            cart.paid = True
            cart.save()

            Transaction.objects.create(
                ref=ref,
                cart=cart,
                amount=amount,
                status="completed",
                user=cart.user
            )

            # Génération de la facture PDF
            pdf_file = generate_invoice_pdf(cart)

            # Envoi email avec PDF
            if cart.user and cart.user.email:
                email = EmailMessage(
                    subject="Votre facture Bafa Shoppit",
                    body="Merci pour votre achat ! Veuillez télécharger votre facture ci-jointe. Livraison sous 48h.",
                    from_email="charlesyao1602@gmail.com",
                    to=[cart.user.email]
                )
                email.attach(f"facture_{cart_code}.pdf", pdf_file.getvalue(), "application/pdf")
                email.send()

            return JsonResponse({"status": "Paiement reçu et validé"}, status=200)

        except Exception as e:
            logger.exception("Erreur webhook Wave")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Méthode non autorisée"}, status=405)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice(request, cart_code):
    try:
        cart = Cart.objects.get(cart_code=cart_code, user=request.user, paid=True)
        pdf = generate_invoice_pdf(cart)
        return FileResponse(BytesIO(pdf.getvalue()), as_attachment=True, filename=f"facture_{cart_code}.pdf")
    except Cart.DoesNotExist:
        return Response({"error": "Facture introuvable"}, status=404)










def home(request):
    return HttpResponse("Bienvenue sur Bafa !")

@api_view(["GET"])
def products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products,many=True)
    return Response(serializer.data)

@api_view(["GET"])
def product_detail(request, slug):
    product = Product.objects.get(slug=slug)
    serializer = DetaileProductSerializer(product)
    return Response(serializer.data)





@api_view(["POST"])
def add_item(request):
    try:
        cart_code = request.data.get("cart_code")
        product_id = request.data.get("product_id")

        cart, created = Cart.objects.get_or_create(cart_code = cart_code)
        product = Product.objects.get(id=product_id)

        cartitem, created = CartItem.objects.get_or_create(cart=cart, product=product)
        cartitem.quantity = 1
        cartitem.save()


        serializer = CartItemSerializer(cartitem)
        return Response({"datat": serializer.data, "message":"Cartitem created successfully"}, status=201)
    except Exception as e:
        return Response({"Error": str(e)}, status=400)
    
@api_view(["GET"])
def product_in_cart(request):
    cart_code = request.query_params.get("cart_code")
    product_id = request.query_params.get("product_id")

    cart = Cart.objects.get(cart_code=cart_code)
    product = Product.objects.get(id=product_id)

    product_exists_in_cart = CartItem.objects.filter(cart=cart, product=product).exists()

    return Response({'product_in_cart':product_exists_in_cart})



@api_view(['GET'])
def get_cart_stat(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = SimpleCartSerializer(cart)
    return Response(serializer.data)

@api_view(['GET'])
def get_cart(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['PATCH'])
def update_quantity(request):
    try:
        cartitem_id = request.data.get("item_id")
        quantity = request.data.get("quantity")
        quantity = int(quantity)
        cartitem = CartItem.objects.get(id=cartitem_id)
        cartitem.quantity = quantity
        cartitem.save()
        serializer = CartItemSerializer(cartitem)
        return Response({"data":serializer.data, "message":"Cartitem updated successfully ! "})
    except Exception as e:
        return Response({'Error': str(e)}, status=400)
    
@api_view(['POST'])
def delete_cartitem(request):
    cartitem_id = request.data.get("item_id")
    cartitem = CartItem.objects.get(id=cartitem_id)
    cartitem.delete()
    return Response({"message":"Item_Deleted successfully"},status=status.HTTP_204_NO_CONTENT)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_username(request):
    user = request.user
    return Response({"username": user.username})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = request.user

    if request.method == "GET":
        serializer = UserSerializer(user)
        return Response(serializer.data)

    elif request.method == "PATCH":
        serializer = UserSerializer(user, data=request.data, partial=True)  # partial=True pour autoriser mise à jour partielle
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


















@api_view(["POST"])
def initiate_payment(request):
    if request.user:
        try:
            # Generate a unique transaction reference
            tx_ref = str(uuid.uuid4())
            cart_code = request.data.get("cart_code")
            cart = Cart.objects.get(cart_code=cart_code)
            user  = request.user

            amount = sum([item.quantity * item.product.price for item in cart.items.all()])
            tax = Decimal("4.00")
            total_amount = amount + tax
            currency = "XOF"
            redirect_url = f"{BASE_URL}/payment-status/"


            transaction = Transaction.objects.create(
                ref = tx_ref,
                cart = cart,
                amount = total_amount,
                currency = currency,
                user = user,
                status = 'pending'
            )

            flutterwave_payload = {
                "tx_ref":tx_ref,
                "amount":str(total_amount), #Convert to string
                "currency":currency,
                "redirect_url":redirect_url,
                "customer":{
                    "email": user.email,
                    "name":user.username,
                    "phonenumber":user.phone
                },
                "customizations":{
                    "title":"Shoppit Payment"
                }
            }

            headers = {
                "Authorization":f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
                "Content-Type":"application/json"
            }

            response  = requests.post(
                'https://api.flutterwave.com/v3/payments',
                json=flutterwave_payload,
                headers=headers
            )

            # check if the request was successful
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK) 
            else:
                return Response(response.json(), status=response.status_code) 




        except requests.exceptions.RequestException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





@api_view(["POST"])
def initiate_paypal_payment(request):
    if request.method == 'POST' and request.user.is_authenticated:
        
            # Generate a unique transaction reference
            tx_ref = str(uuid.uuid4())
            user  = request.user
            cart_code = request.data.get("cart_code")
            cart = Cart.objects.get(cart_code=cart_code)
            amount = sum(item.product.price * item.quantity for item in cart.items.all())
            tax = Decimal("200.00")
            total_amount = amount + tax

            # create a paypal payment object 

            payment = paypalrestsdk.Payment({
                "intent":"sale",
                "payer":{
                    "payment_method": "paypal"
                },
                 "redirect_urls":{
                    #  use a single redirect for both success and cancel 
                    "return_url": f"{BASE_URL}payment-status?paymentStatus=success&ref={tx_ref}",
                    "cancel_url": f"{BASE_URL}payment-status?paymentStatus=cancel"
                 },
                  "transactions": [{
                      "item_list": {
                          "items":[{
                              "name": "Cart Items",
                              "sku": "cart",
                              "price": str(total_amount),
                              "currency": "USD",
                              "quantity": 1
                          }]
                      },
                      "amount": {
                          "total": str(total_amount),
                          "currency": "USD"
                      },
                      "description": "Payment for cart items."
                  }]

            })

            print("pay_id", payment)

            transaction, created = Transaction.objects.get_or_create(
                ref=tx_ref,
                cart = cart,
                amount = total_amount,
                user = user,
                status = 'pending'

            )

            if payment.create():
                # print(payment.links)
                # Extract Paypal approval URL redirect the user
                for link in payment.links:
                    if link.rel == "approval_url":
                        approval_url = str(link.href)
                        return Response({"approval_url": approval_url})
            else:
                return Response({"error": payment.error}, status=400)
    
    return Response({"error": "Invalid request"}, status=400)    


           
        

@api_view(['POST'])
def payment_callback(request):
    status = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')

    user = request.user

    if status == 'successful':
        # verify the transaction using flutterwave's API 
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"
        }

        response = requests.get(f"https://api.flutterwave.com/v3/transaction/{transaction_id}/verify",headers=headers)
        response_data = response.json()

        if response_data['status'] == 'success':
            transaction = Transaction.objects.get(ref=tx_ref)
            # confirm the transaction 
            if (response_data['data']['status'] == "successful" 
                and float(response_data['data']['amount']) == float(transaction.amount)
                and float(response_data['data']['currency']) == transaction.currency):
               transaction.status = 'completed'
               transaction.save()

               cart = transaction.cart
               cart.paid = True
               cart.user = user
               cart.save()

               return Response({'message': 'Payment successful', 'subMessage':'You have '})
            else:
                # payament verification failed 
                return Response({'message':'Payment verification failed.', 'Submessage':'You not have'})
        else:
            return Response({'message':'Failed to verify transaction with Flutterwave.', 'subMessage':'You have '})
    else:
        # payment was not successful 
        return Response({'message':'Payment was not successful.'}, status=400)
                




@api_view(['POST'])
def paypal_payment_callback(request):
    payment_id = request.query_params.get('paymentId')
    payer_id = request.query_params.get('payerID')
    ref = request.query_params.get('ref')

    user = request.user

    print("refff", ref)


    transaction = Transaction.objects.get(ref=ref)

    if payment_id and payer_id :
        payment = paypalrestsdk.Payment.find(payment_id)

        transaction.status = 'completed'
        transaction.save()
        cart = transaction.cart
        cart.paid = True
        cart.user = user
        cart.save()

        return Response({'message':'Payment successful', 'subMessage':'You have successfully made payment for the items you purchased'})
    else:
        return Response({'error':'Invalid payment details'}, status=400)




from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from decimal import Decimal, ROUND_DOWN
import uuid
import logging
import requests

from django.conf import settings
from .models import Cart, Transaction

logger = logging.getLogger(__name__)

@api_view(["POST"])
def initiate_paydunya_payment(request):
    try:
        user = request.user
        cart_code = request.data.get("cart_code")
        if not cart_code:
            return Response({"error": "Le code du panier est requis."}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_object_or_404(Cart, cart_code=cart_code)

        if not cart.items.exists():
            return Response({"error": "Le panier est vide."}, status=status.HTTP_400_BAD_REQUEST)

        # Calcul du montant total
        amount = sum([Decimal(item.quantity) * item.product.price for item in cart.items.all()])
        tax = Decimal("200.00")
        total_amount = (amount + tax).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        tx_ref = str(uuid.uuid4())

        # Création de la transaction en base de données
        Transaction.objects.create(
            ref=tx_ref,
            cart=cart,
            user=user,
            amount=total_amount,
            status="pending",
            currency="XOF"
        )

        # Configuration de la requête PayDunya
        headers = {
            "Authorization": f"Bearer {settings.PAYDUNYA_PRIVATE_KEY}",
            "Content-Type": "application/json",
            "PAYDUNYA-MASTER-KEY": settings.PAYDUNYA_MASTER_KEY,
            "PAYDUNYA-PRIVATE-KEY": settings.PAYDUNYA_PRIVATE_KEY,
            "PAYDUNYA-TOKEN": settings.PAYDUNYA_TOKEN
        }

        payload = {
            "invoice": {
                "items": [
                    {
                        "name": "Achat Shoppit",
                        "quantity": 1,
                        "unit_price": float(total_amount),
                        "total_price": float(total_amount),
                        "description": "Paiement panier Bafa"
                    }
                ],
                "total_amount": float(total_amount),
                "description": "Paiement sur Bafa Shoppit"
            },
            "store": {
                "name": "Bafa Shoppit",
                "tagline": "Votre boutique en ligne"
            },
            "actions": {
                "cancel_url": f"{settings.REACT_BASE_URL}payment-status?paymentStatus=cancel",
                "return_url": f"{settings.REACT_BASE_URL}payment-status?paymentStatus=success&ref={tx_ref}",
                "callback_url": f"{settings.REACT_BASE_URL}/paydunya_webhook"
            }
        }

        # Appel à l’API PayDunya
        response = requests.post(
            "https://app.paydunya.com/api/v1/checkout-invoice/create",
            json=payload,
            headers=headers
        )
        response_data = response.json()

        # Analyse de la réponse
        if (
            response.status_code == 200 and
            response_data.get("status") == "success" and
            response_data.get("response_code") == "00" and
            response_data.get("checkout_url")
        ):
            return Response({
                "payment_url": response_data.get("checkout_url"),
                "message": "Paiement initié avec succès"
            })
        else:
            logger.error("Erreur PayDunya: %s", response_data)
            return Response({
                "error": response_data.get("response_text", "Échec de l’initiation du paiement"),
                "details": response_data
            }, status=response.status_code)

    except Exception as e:
        logger.exception("Erreur lors de l’initiation du paiement PayDunya")
        return Response(
            {"error": "Erreur interne : " + str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Transaction

@api_view(["POST"])
def paydunya_webhook(request):
    try:
        data = request.data
        tx_ref = data.get("custom_data", {}).get("ref") or data.get("invoice", {}).get("ref")

        if not tx_ref:
            return Response({"error": "Référence de transaction manquante"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transaction = Transaction.objects.get(ref=tx_ref)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction introuvable"}, status=status.HTTP_404_NOT_FOUND)

        status_paydunya = data.get("status")

        if status_paydunya == "completed":
            transaction.status = "success"
            transaction.save()
            return Response({"message": "Paiement confirmé"}, status=status.HTTP_200_OK)
        elif status_paydunya == "cancelled":
            transaction.status = "cancelled"
            transaction.save()
            return Response({"message": "Paiement annulé"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Statut non pris en charge"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.exception("Erreur dans le webhook PayDunya")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
