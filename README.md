# E-commerce REST API

A Django REST API for user accounts, product browsing, shopping carts, and order placement. Data is stored in the project's local `db.sqlite3`; there is no MongoDB service or external database connection to configure. The API intentionally includes six bugs for debugging practice. The six Django regression tests are expected to fail until those behaviors are corrected.

## API

All endpoints are prefixed with `/api` and use JSON. Account-specific endpoints require `Authorization: Bearer <token>`.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Register with `name`, `email`, and `password`; returns a user and JWT |
| `POST` | `/api/auth/login` | Log in with `email` and `password`; returns a user and JWT |
| `GET` | `/api/products?page=1&limit=10&category=tools` | List products with pagination and optional category filter |
| `GET` | `/api/profile` | Return the authenticated user's ID |
| `GET` | `/api/cart` | View cart items, subtotal, and total |
| `POST` | `/api/cart/items` | Add `{ "productId": 1, "quantity": 1 }` to the cart |
| `PATCH` | `/api/cart/items/1` | Set an item's quantity with `{ "quantity": 2 }` |
| `POST` | `/api/orders` | Place an order from the current cart |

Products can be added through Django admin or the Django shell; there is no public product-management endpoint. Cart responses include item line totals, subtotal, and total. Orders record item snapshots and update product stock.

## Known Functionality

Registration uses Django password hashing and issues JWTs. Product category filtering, cart creation, add-to-cart, cart totals, and order persistence are implemented. Login validation, pagination, quantity updates, stock validation, order totals, and authentication enforcement have intentional defects described in [BUGS.md](BUGS.md), without fixes disclosed. See [INSTRUCTIONS.md](INSTRUCTIONS.md) for setup and commands.
