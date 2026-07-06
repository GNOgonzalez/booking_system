"""Studio sign-in branding — display name and logo."""

from scheduling.models import StudioBranding
from scheduling.services.uploads import validate_logo


def branding_payload(*, request=None):
    branding = StudioBranding.load()
    logo_url = None
    if branding.logo:
        url = branding.logo.url
        if request is not None:
            logo_url = request.build_absolute_uri(url)
        else:
            logo_url = url
    return {
        'display_name': branding.display_name,
        'logo_url': logo_url,
    }


def update_branding(*, display_name=None, logo=None, clear_logo=False):
    branding = StudioBranding.load()
    if display_name is not None:
        name = display_name.strip()
        if not name:
            return None, 'Display name is required.'
        branding.display_name = name[:120]
    if logo is not None:
        error = validate_logo(logo)
        if error:
            return None, error
        if branding.logo:
            branding.logo.delete(save=False)
        branding.logo = logo
    elif clear_logo and branding.logo:
        branding.logo.delete(save=False)
        branding.logo = ''
    branding.save()
    return branding, None
