from django.contrib import admin
from .models import Product, Cart, CartItem, Transaction

admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Transaction)