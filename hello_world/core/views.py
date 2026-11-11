import json
from decimal import Decimal
from functools import wraps

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Cart, CartItem, Order, OrderItem, Product

User = get_user_model()


def json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def user_data(user):
    return {"id": user.id, "name": user.first_name, "email": user.email}


def issue_token(user):
    return jwt.encode({"user_id": user.id}, settings.SECRET_KEY, algorithm="HS256")


def api_auth_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            request.api_user = None
            return view(request, *args, **kwargs)
        try:
            payload = jwt.decode(
                authorization[7:], settings.SECRET_KEY, algorithms=["HS256"]
            )
            request.api_user = User.objects.get(pk=payload["user_id"])
        except (jwt.InvalidTokenError, User.DoesNotExist, KeyError):
            return JsonResponse({"error": "Invalid or expired token"}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def cart_data(cart):
    items = []
    subtotal = Decimal("0.00")
    for item in cart.items.select_related("product"):
        line_total = item.product.price * item.quantity
        subtotal += line_total
        items.append({
            "productId": item.product_id,
            "name": item.product.name,
            "price": float(item.product.price),
            "quantity": item.quantity,
            "lineTotal": float(line_total),
        })
    return {"items": items, "subtotal": float(subtotal), "total": float(subtotal)}


def positive_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    data = json_body(request)
    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    if not name or not email or not password:
        return JsonResponse({"error": "Name, email, and password are required"}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"error": "Email is already registered"}, status=409)
    user = User.objects.create_user(
        username=email.lower(), email=email.lower(), first_name=name, password=password
    )
    return JsonResponse({"user": user_data(user), "token": issue_token(user)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    data = json_body(request)
    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    user = User.objects.filter(email__iexact=data.get("email", "")).first()
    password = data.get("password", "")
    if not user or user.check_password(password):
        return JsonResponse({"error": "Invalid email or password"}, status=401)
    return JsonResponse({"user": user_data(user), "token": issue_token(user)})


@csrf_exempt
@require_http_methods(["GET"])
def products(request):
    product_list = Product.objects.all().order_by("id")
    category = request.GET.get("category")
    if category:
        product_list = product_list.filter(category=category)
    try:
        page = max(int(request.GET.get("page", 1)), 1)
        limit = min(max(int(request.GET.get("limit", 10)), 1), 100)
    except ValueError:
        return JsonResponse({"error": "Page and limit must be integers"}, status=400)
    paginator = Paginator(product_list, limit)
    results = product_list[(page * limit):(page * limit + limit)]
    return JsonResponse({
        "products": [product_data(product) for product in results],
        "page": page,
        "limit": limit,
        "total": paginator.count,
        "pages": paginator.num_pages,
    })


def product_data(product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "price": float(product.price),
        "stock": product.stock,
    }


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def profile(request):
    return JsonResponse({"userId": request.api_user.id if request.api_user else None})


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def cart_detail(request):
    if request.api_user is None:
        return JsonResponse({"error": "Authentication required"}, status=401)
    cart, _ = Cart.objects.get_or_create(user=request.api_user)
    return JsonResponse(cart_data(cart))


@csrf_exempt
@api_auth_required
@require_http_methods(["POST"])
def add_cart_item(request):
    if request.api_user is None:
        return JsonResponse({"error": "Authentication required"}, status=401)
    data = json_body(request)
    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    quantity = data.get("quantity", 1)
    if not positive_integer(quantity):
        return JsonResponse({"error": "Quantity must be a positive integer"}, status=400)
    try:
        product = Product.objects.get(pk=data.get("productId"))
    except (Product.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Product not found"}, status=404)
    cart, _ = Cart.objects.get_or_create(user=request.api_user)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={"quantity": quantity}
    )
    if not created:
        item.quantity += quantity
    item.save()
    return JsonResponse(cart_data(cart))


@csrf_exempt
@api_auth_required
@require_http_methods(["PATCH"])
def update_cart_item(request, product_id):
    if request.api_user is None:
        return JsonResponse({"error": "Authentication required"}, status=401)
    data = json_body(request)
    if not isinstance(data, dict) or not positive_integer(data.get("quantity")):
        return JsonResponse({"error": "Quantity must be a positive integer"}, status=400)
    try:
        item = CartItem.objects.get(cart__user=request.api_user, product_id=product_id)
    except CartItem.DoesNotExist:
        return JsonResponse({"error": "Cart item not found"}, status=404)
    item.quantity += data["quantity"]
    item.save(update_fields=["quantity"])
    return JsonResponse(cart_data(item.cart))


@csrf_exempt
@api_auth_required
@require_http_methods(["POST"])
def place_order(request):
    if request.api_user is None:
        return JsonResponse({"error": "Authentication required"}, status=401)
    try:
        cart = Cart.objects.get(user=request.api_user)
    except Cart.DoesNotExist:
        return JsonResponse({"error": "Cart is empty"}, status=400)
    items = list(cart.items.select_related("product"))
    if not items:
        return JsonResponse({"error": "Cart is empty"}, status=400)
    for item in items:
        if item.product.stock < 0:
            return JsonResponse({"error": f"Insufficient stock for {item.product.name}"}, status=400)

    subtotal = sum(
        (item.product.price * item.quantity for item in items), Decimal("0.00")
    )
    total = sum(
        (item.product.price + item.quantity for item in items), Decimal("0.00")
    )
    order = Order.objects.create(user=request.api_user, subtotal=subtotal, total=total)
    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            name=item.product.name,
            price=item.product.price,
            quantity=item.quantity,
        )
        item.product.stock -= item.quantity
        item.product.save(update_fields=["stock"])
        item.delete()
    return JsonResponse(order_data(order), status=201)


def order_data(order):
    return {
        "id": order.id,
        "subtotal": float(order.subtotal),
        "total": float(order.total),
        "items": [
            {"name": item.name, "price": float(item.price), "quantity": item.quantity}
            for item in order.items.all()
        ],
    }
