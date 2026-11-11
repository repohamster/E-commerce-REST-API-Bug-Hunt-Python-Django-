from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem, Product


admin.site.register([Product, Cart, CartItem, Order, OrderItem])
