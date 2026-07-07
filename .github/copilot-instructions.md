# Copilot Instructions for sharp_student_documents

## Project Overview
This is a Django-based platform for buying and selling academic documents. It supports user registration, document uploads, purchases, reviews, and payments via Stripe and PayPal. The architecture is modular, with each app handling a distinct domain:
- `accounts`: Custom user model, registration, authentication, profile management
- `documents`: Document upload, preview, purchase, and download
- `payments`: Payment processing and integration (Stripe, PayPal)
- `reviews`: Document reviews and ratings
- `sales`: Seller dashboard and analytics

## Key Architectural Patterns
- **Custom User Model**: Defined in `accounts.models.CustomUser` (see `AUTH_USER_MODEL` in settings)
- **Document Storage**: Uses Cloudinary for secure file storage (`CloudinaryField` in `documents.models.Document`)
- **Payments**: Stripe and PayPal SDKs are configured in `settings.py` and used in `payments/services.py`. Payment status is tracked in `payments.models.Payment` and `documents.models.Order`.
- **Preview Extraction**: Document previews and page counts are generated in `documents/views.py::generate_preview` for PDF, DOCX, and TXT files.
- **Purchasing Flow**: Orders are created in `documents.models.Order`, with payment initiated via `payments/services.py` and tracked in `payments.models.Payment`.
- **Reviews**: Linked to documents via foreign key, aggregated in document list/detail views.

## Developer Workflows
- **Run Server**: `python manage.py runserver`
- **Migrations**: `python manage.py makemigrations` and `python manage.py migrate`
- **Create Superuser**: `python manage.py createsuperuser`
- **Test**: `python manage.py test [app]`
- **Static/Media**: Static files in `/static/`, media via Cloudinary
- **Environment Variables**: Use `.env` for secrets (see `settings.py` for required keys)

## Project-Specific Conventions
- **Slug Usage**: Documents use slugs for URLs; auto-generated from title if not provided
- **Order & Payment Status**: Status fields use explicit choices (see models)
- **App Structure**: Each app has its own `models.py`, `views.py`, `urls.py`, `forms.py`, and templates
- **Template Organization**: Project-level templates in `/templates/`, app-specific in `app/templates/app/`
- **Third-Party Services**: Cloudinary for file storage, Stripe/PayPal for payments

## Integration Points
- **Stripe/PayPal**: API keys and webhook secrets must be set in environment and `settings.py`
- **Cloudinary**: Requires API credentials in `.env` and `settings.py`
- **Email**: Configured for SMTP and console backend in `settings.py`

## Examples
- To add a new payment method, extend `PAYMENT_METHODS` in `payments/models.py` and update `payments/services.py`
- To customize document preview logic, edit `generate_preview` in `documents/views.py`
- To add seller analytics, use `sales/` app and aggregate data from `Order` and `Payment`

---

If any section is unclear or missing, please provide feedback so this guide can be improved for future AI agents.
