from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from accounts.decorators import force_login_check
from configuration.cache import delete_configuration_cache
from configuration.models import Configuration


@login_required
@force_login_check
def delete_caches(request):
    """
    Delete all the caches.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

    Returns:
        ``HttpResponse``. A rendered Http Response (redirected to the
        search admin home page).
    """
    if request.user.is_superuser is not True:
        raise PermissionDenied()

    active_configurations = Configuration.objects.filter(active=True)
    for configuration in active_configurations:
        delete_configuration_cache(configuration)

    messages.success(request, 'Caches deleted.')

    return redirect('search:admin')
