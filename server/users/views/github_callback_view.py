from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from users.github import (
    GitHubOAuthError,
    exchange_code_for_token_data,
    fetch_github_emails,
    fetch_github_user,
    select_email,
)
from users.services import get_tokens_for_user, user_create_or_update_from_github
from users.views.constants import GITHUB_OAUTH_STATE_SESSION_KEY


@method_decorator(never_cache, name='dispatch')
class GitHubCallbackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        expected_state = request.session.get(GITHUB_OAUTH_STATE_SESSION_KEY)

        if not expected_state or not state or not constant_time_compare(expected_state, state):
            raise AuthenticationFailed('Invalid GitHub OAuth state')
        # Consume a matching state once, while keeping valid attempts intact on mismatch.
        request.session.pop(GITHUB_OAUTH_STATE_SESSION_KEY)
        if request.query_params.get('error'):
            detail = request.query_params.get('error_description') or request.query_params['error']
            raise ValidationError({'detail': detail})
        if not code:
            raise ValidationError({'detail': 'Missing GitHub OAuth code'})

        try:
            token_data = exchange_code_for_token_data(code=code)
            access_token = token_data['access_token']
            github_user = fetch_github_user(access_token=access_token)
            github_emails = fetch_github_emails(access_token=access_token)
            email = select_email(github_user=github_user, github_emails=github_emails)
            user = user_create_or_update_from_github(
                github_user=github_user,
                access_token=access_token,
                token_data=token_data,
                email=email,
            )
        except GitHubOAuthError as exc:
            raise AuthenticationFailed(str(exc)) from exc
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc

        tokens = get_tokens_for_user(user)

        params = urlencode({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        })
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/login?{params}")
