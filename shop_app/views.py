from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from .models import Product, Cart, CartItem, Transaction
from .serializers import (
    ProductSerializer, 
    DetaileProductSerializer, 
    CartItemSerializer, 
    SimpleCartSerializer, 
    CartSerializer, 
    UserSerializer
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse

# Payment 
from decimal import Decimal
import uuid
from django.conf import settings 
import requests
import paypalrestsdk
from django.core.exceptions import ObjectDoesNotExist

BASE_URL = settings.REACT_BASE_URL

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

def home(request):
    return HttpResponse("Bienvenue sur Bafa !")

@api_view(["GET"])
def products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def product_detail(request, slug):
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)
    serializer = DetaileProductSerializer(product)
    return Response(serializer.data)

@api_view(["POST"])
def add_item(request):
    try:
        cart_code = request.data.get("cart_code")
        product_id = request.data.get("product_id")

        cart, _ = Cart.objects.get_or_create(cart_code=cart_code)
        product = Product.objects.get(id=product_id)

        cartitem, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if created:
            cartitem.quantity = 1
        cartitem.save()

        serializer = CartItemSerializer(cartitem)
        return Response({"data": serializer.data, "message": "Cart item created successfully"}, status=201)
    except ObjectDoesNotExist:
        return Response({"error": "Product or Cart not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(["GET"])
def product_in_cart(request):
    try:
        cart_code = request.query_params.get("cart_code")
        product_id = request.query_params.get("product_id")

        cart = Cart.objects.get(cart_code=cart_code)
        product = Product.objects.get(id=product_id)

        product_exists_in_cart = CartItem.objects.filter(cart=cart, product=product).exists()

        return Response({'product_in_cart': product_exists_in_cart})
    except ObjectDoesNotExist:
        return Response({'error': 'Cart or Product not found'}, status=404)

@api_view(["GET"])
def get_cart_stat(request):
    try:
        cart_code = request.query_params.get("cart_code")
        cart = Cart.objects.get(cart_code=cart_code, paid=False)
        serializer = SimpleCartSerializer(cart)
        return Response(serializer.data)
    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found'}, status=404)

@api_view(["GET"])
def get_cart(request):
    try:
        cart_code = request.query_params.get("cart_code")
        cart = Cart.objects.get(cart_code=cart_code, paid=False)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found'}, status=404)

@api_view(["PATCH"])
def update_quantity(request):
    try:
        cartitem_id = request.data.get("item_id")
        quantity = int(request.data.get("quantity", 1))

        cartitem = CartItem.objects.get(id=cartitem_id)
        cartitem.quantity = quantity
        cartitem.save()

        serializer = CartItemSerializer(cartitem)
        return Response({"data": serializer.data, "message": "Cart item updated successfully!"})
    except CartItem.DoesNotExist:
        return Response({'error': 'CartItem not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(["POST"])
def delete_cartitem(request):
    try:
        cartitem_id = request.data.get("item_id")
        cartitem = CartItem.objects.get(id=cartitem_id)
        cartitem.delete()
        return Response({"message": "Item deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    except CartItem.DoesNotExist:
        return Response({'error': 'CartItem not found'}, status=404)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_username(request):
    return Response({"username": request.user.username})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(["POST"])
def initiate_payment(request):
    if request.user.is_authenticated:
        try:
            tx_ref = str(uuid.uuid4())
            cart_code = request.data.get("cart_code")
            cart = Cart.objects.get(cart_code=cart_code)

            amount = sum([item.quantity * item.product.price for item in cart.items.all()])
            tax = Decimal("4.00")
            total_amount = amount + tax
            currency = "XOF"
            redirect_url = f"{BASE_URL}/payment-status/"

            transaction = Transaction.objects.create(
                ref=tx_ref,
                cart=cart,
                amount=total_amount,
                currency=currency,
                user=request.user,
                status='pending'
            )

            flutterwave_payload = {
                "tx_ref": tx_ref,
                "amount": str(total_amount),
                "currency": currency,
                "redirect_url": redirect_url,
                "customer": {
                    "email": request.user.email,
                    "name": request.user.username,
                    "phonenumber": getattr(request.user, 'phone', '')
                },
                "customizations": {
                    "title": "Shoppit Payment"
                }
            }

            headers = {
                "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                'https://api.flutterwave.com/v3/payments',
                json=flutterwave_payload,
                headers=headers
            )

            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response(response.json(), status=response.status_code)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=404)
        except requests.exceptions.RequestException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({"error": "Authentication required"}, status=401)

@api_view(["POST"])
def initiate_paypal_payment(request):
    if request.user.is_authenticated:
        try:
            tx_ref = str(uuid.uuid4())
            cart_code = request.data.get("cart_code")
            cart = Cart.objects.get(cart_code=cart_code)

            amount = sum(item.product.price * item.quantity for item in cart.items.all())
            tax = Decimal("200.00")
            total_amount = amount + tax

            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": f"{BASE_URL}payment-status?paymentStatus=success&ref={tx_ref}",
                    "cancel_url": f"{BASE_URL}payment-status?paymentStatus=cancel"
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
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

            transaction, _ = Transaction.objects.get_or_create(
                ref=tx_ref,
                cart=cart,
                amount=total_amount,
                user=request.user,
                status='pending'
            )

            if payment.create():
                for link in payment.links:
                    if link.rel == "approval_url":
                        return Response({"approval_url": str(link.href)})
            else:
                return Response({"error": payment.error}, status=400)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=404)
    return Response({"error": "Authentication required"}, status=401)

@api_view(["POST"])
def payment_callback(request):
    status_param = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')

    if status_param == 'successful':
        headers = {"Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"}
        response = requests.get(f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify", headers=headers)
        response_data = response.json()

        if response_data['status'] == 'success':
            transaction = Transaction.objects.get(ref=tx_ref)
            if (response_data['data']['status'] == "successful" and
                float(response_data['data']['amount']) == float(transaction.amount) and
                response_data['data']['currency'] == transaction.currency):
                
                transaction.status = 'completed'
                transaction.save()

                cart = transaction.cart
                cart.paid = True
                cart.user = request.user
                cart.save()

                return Response({'message': 'Payment successful'})
            else:
                return Response({'message': 'Payment verification failed.'}, status=400)
        else:
            return Response({'message': 'Failed to verify transaction.'}, status=400)
    return Response({'message': 'Payment was not successful.'}, status=400)

@api_view(["POST"])
def paypal_payment_callback(request):
    payment_id = request.query_params.get('paymentId')
    payer_id = request.query_params.get('payerID')
    ref = request.query_params.get('ref')

    if payment_id and payer_id:
        payment = paypalrestsdk.Payment.find(payment_id)
        transaction = Transaction.objects.get(ref=ref)

        transaction.status = 'completed'
        transaction.save()

        cart = transaction.cart
        cart.paid = True
        cart.user = request.user
        cart.save()

        return Response({'message': 'Payment successful'})
    else:
        return Response({'error': 'Invalid payment details'}, status=400)
