"""Shared upload size and type validation."""

import os

from django.conf import settings


def max_homework_bytes():
    return getattr(settings, 'MAX_HOMEWORK_UPLOAD_BYTES', 10 * 1024 * 1024)


def max_blog_image_bytes():
    return getattr(settings, 'MAX_BLOG_IMAGE_BYTES', 5 * 1024 * 1024)


def max_logo_bytes():
    return getattr(settings, 'MAX_LOGO_BYTES', 2 * 1024 * 1024)


def upload_limits_payload():
    homework_mb = max_homework_bytes() // (1024 * 1024)
    blog_mb = max_blog_image_bytes() // (1024 * 1024)
    logo_mb = max_logo_bytes() // (1024 * 1024)
    return {
        'homework_max_bytes': max_homework_bytes(),
        'homework_max_mb': homework_mb,
        'homework_extensions': sorted(settings.ALLOWED_HOMEWORK_EXTENSIONS),
        'blog_image_max_bytes': max_blog_image_bytes(),
        'blog_image_max_mb': blog_mb,
        'blog_image_extensions': sorted(settings.ALLOWED_BLOG_IMAGE_EXTENSIONS),
        'logo_max_bytes': max_logo_bytes(),
        'logo_max_mb': logo_mb,
        'logo_extensions': sorted(settings.ALLOWED_LOGO_EXTENSIONS),
    }


def _extension(filename):
    _, ext = os.path.splitext((filename or '').lower())
    return ext


def validate_file_size(uploaded_file, max_bytes, *, label='File'):
    if uploaded_file is None:
        return None
    if uploaded_file.size > max_bytes:
        mb = max_bytes // (1024 * 1024)
        return f'{label} must be {mb} MB or smaller.'
    return None


def validate_homework_file(uploaded_file):
    if uploaded_file is None:
        return None
    error = validate_file_size(uploaded_file, max_homework_bytes(), label='File')
    if error:
        return error
    ext = _extension(uploaded_file.name)
    if ext and ext not in settings.ALLOWED_HOMEWORK_EXTENSIONS:
        allowed = ', '.join(sorted(settings.ALLOWED_HOMEWORK_EXTENSIONS))
        return f'File type not allowed. Use: {allowed}'
    return None


def validate_blog_image(uploaded_file):
    if uploaded_file is None:
        return None
    error = validate_file_size(uploaded_file, max_blog_image_bytes(), label='Image')
    if error:
        return error
    ext = _extension(uploaded_file.name)
    if ext not in settings.ALLOWED_BLOG_IMAGE_EXTENSIONS:
        allowed = ', '.join(sorted(settings.ALLOWED_BLOG_IMAGE_EXTENSIONS))
        return f'Image type not allowed. Use: {allowed}'
    return None


def validate_logo(uploaded_file):
    if uploaded_file is None:
        return None
    error = validate_file_size(uploaded_file, max_logo_bytes(), label='Logo')
    if error:
        return error
    ext = _extension(uploaded_file.name)
    if ext not in settings.ALLOWED_LOGO_EXTENSIONS:
        allowed = ', '.join(sorted(settings.ALLOWED_LOGO_EXTENSIONS))
        return f'Logo type not allowed. Use: {allowed}'
    return None
