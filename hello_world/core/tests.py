from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import CartItem, Order, Product

User = get_user_model()


class EcommerceApiBugTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            first_name="Test User",
            password="correct-password",
        )
        from .views import issue_token

        self.token = issue_token(self.user)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def create_product(self, **overrides):
        values = {"name": "Test product", "category": "tools", "price": "10.00", "stock": 20}
        values.update(overrides)
        return Product.objects.create(**values)

    def add_to_cart(self, product, quantity=1):
        return self.client.post(
            "/api/cart/items",
            data={"productId": product.pk, "quantity": quantity},
            content_type="application/json",
            **self.auth,
        )

    def test_login_rejects_an_incorrect_password(self):
        response = self.client.post(
            "/api/auth/login",
            data={"email": self.user.email, "password": "wrong-password"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_product_pagination_returns_the_requested_page(self):
        products = [
            self.create_product(name=f"Product {index}") for index in range(1, 7)
        ]
        response = self.client.get("/api/products?page=2&limit=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product["id"] for product in response.json()["products"]],
            [product.pk for product in products[2:4]],
        )

    def test_updating_a_cart_item_sets_its_quantity(self):
        product = self.create_product()
        self.add_to_cart(product, 1)
        response = self.client.patch(
            f"/api/cart/items/{product.pk}",
            data={"quantity": 3},
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["quantity"], 3)

    def test_order_rejects_quantities_above_available_stock(self):
        product = self.create_product(stock=1)
        self.add_to_cart(product, 2)
        response = self.client.post("/api/orders", **self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_total_matches_item_prices_times_quantities(self):
        product = self.create_product(price="10.00", stock=5)
        self.add_to_cart(product, 2)
        response = self.client.post("/api/orders", **self.auth)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["subtotal"], 20.0)
        self.assertEqual(response.json()["total"], 20.0)

    def test_protected_routes_reject_requests_without_a_jwt(self):
        response = self.client.get("/api/profile")
        self.assertEqual(response.status_code, 401)
