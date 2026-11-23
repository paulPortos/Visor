import secrets
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from users.github import build_github_authorization_url
from users.views.constants import GITHUB_OAUTH_STATE_SESSION_KEY


@method_decorator(never_cache, name='dispatch')
class GitHubLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        callback = urlsplit(settings.GITHUB_CALLBACK_URL)
        if request.get_host().lower() != callback.netloc.lower():
            # Establish the session on the host that will receive GitHub's callback.
            return HttpResponseRedirect(urlunsplit((
                callback.scheme, callback.netloc, request.path, '', '',
            )))

        state = secrets.token_urlsafe(32)
        request.session[GITHUB_OAUTH_STATE_SESSION_KEY] = state
        request.session.save()
        request.session.modified = True
        return HttpResponseRedirect(build_github_authorization_url(state=state))
