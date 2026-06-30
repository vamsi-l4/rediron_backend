# RedIron Backend

Django REST Framework backend for RedIron Fitness. It powers gym content, exercise videos, nutrition articles, user profiles, shop products, cart, checkout, orders, wishlist, and supporting ecommerce pages.

## Tech Stack

- Django and Django REST Framework
- Clerk-authenticated API access
- PostgreSQL or SQLite for local development
- Django media storage for profile, product, equipment, and exercise images
- Email notifications through Django email settings

## Project Structure

- `accounts/` - Custom user model, Clerk-backed profile setup, profile image upload, activity data
- `main/` - Equipment, exercises, nutrition articles, workout tips, fitness articles, performance lab models
- `rediron_shop/` - Categories, products, variants, cart, wishlist, checkout orders, order cancellation
- `rediron_site/` - Settings, URL routing, ASGI/WSGI configuration
- `media/` - Uploaded and imported media files
- `fixtures/` - Seed and import data for articles, exercises, products, and equipment

## Authentication

The backend expects Clerk JWTs from the frontend. `accounts.authentication.ClerkAuthentication` resolves or creates the local `CustomUser` using Clerk identity data. User profile, cart, and wishlist records are initialized after login/signup.

## Checkout And Orders

Orders are created from the authenticated user cart. Inventory is validated before order creation, order items are snapshotted, and the cart is cleared after success. Cash on Delivery is the active payment method while Razorpay is paused. Order confirmation and cancellation emails are sent to the customer and to the configured admin recipient.

## Environment

Create `.env`:

```bash
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CLERK_SECRET_KEY=sk_test_xxx
DATABASE_URL=sqlite:///db.sqlite3
DEFAULT_FROM_EMAIL=RedIron Fitness <your-email@gmail.com>
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
```

## Local Development

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

API runs at `http://127.0.0.1:8000`.

## Useful Commands

```bash
python manage.py showmigrations
python manage.py import_all_data
python manage.py load_initial_data
python manage.py test
```

## Notes

Clerk controls the verification email template. To change signup OTP branding from “Login App” to RedIron Fitness, update the Clerk Dashboard email template and application branding.
