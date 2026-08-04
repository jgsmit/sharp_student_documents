from django.conf import settings


def cloudinary_upload(request):
    return {
        "CLOUDINARY_CLOUD_NAME": settings.CLOUDINARY_STORAGE.get("CLOUD_NAME") or "",
        "CLOUDINARY_UPLOAD_PRESET": settings.CLOUDINARY_UPLOAD_PRESET,
    }
