from django.urls import path
from . import views
# c'est moi charles
urlpatterns = [
    path("products", views.products, name="products")
]
