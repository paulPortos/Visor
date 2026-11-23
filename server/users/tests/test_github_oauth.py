from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status

from users.models import User
from users.views import GITHUB_OAUTH_STATE_SESSION_KEY


@override_settings(
    GITHUB_CLIENT_ID='client-id',
    GITHUB_CLIENT_SECRET='client-secret',
    GITHUB_CALLBACK_URL='http://localhost:8000/auth/github/callback/',
    FRONTEND_URL='http://localhost:3000',
)
class GitHubOAuthTests(TestCase):
    def test_login_redirects_to_github_and_stores_state(self):
        response = self.client.get(reverse('auth:github-oauth-login'), HTTP_HOST='localhost:8000')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        parsed = urlparse(response['Location'])
        query = parse_qs(parsed.query)
        session = self.client.session

        self.assertEqual(f'{parsed.scheme}://{parsed.netloc}{parsed.path}', 'https://github.com/login/oauth/authorize')
        self.assertEqual(query['client_id'], ['client-id'])
        self.assertEqual(query['redirect_uri'], ['http://localhost:8000/auth/github/callback/'])
        self.assertEqual(query['scope'], ['read:user user:email repo'])
        self.assertEqual(query['state'], [session[GITHUB_OAUTH_STATE_SESSION_KEY]])
        self.assertIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertIn('no-store', response['Cache-Control'])

    def test_login_canonicalizes_the_callback_host_before_creating_a_session(self):
        response = self.client.get(reverse('auth:github-oauth-login'), HTTP_HOST='127.0.0.1:8000')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response['Location'], 'http://localhost:8000/auth/github/login/')
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertIn('no-store', response['Cache-Control'])

        canonical_response = self.client.get(response['Location'], HTTP_HOST='localhost:8000')
        self.assertEqual(urlparse(canonical_response['Location']).hostname, 'github.com')
        self.assertIn(settings.SESSION_COOKIE_NAME, canonical_response.cookies)

    def test_login_canonicalizes_the_port_before_creating_a_session(self):
        response = self.client.get(reverse('auth:github-oauth-login'), HTTP_HOST='localhost:3000')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response['Location'], 'http://localhost:8000/auth/github/login/')
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)

    @override_settings(SESSION_COOKIE_NAME='visor_docker_sessionid')
    def test_docker_cookie_does_not_replace_other_local_application_sessions(self):
        self.client.cookies['sessionid'] = 'other-application-session'
        self.client.cookies['visor_sessionid'] = 'native-visor-session'
        response = self.client.get(reverse('auth:github-oauth-login'), HTTP_HOST='localhost:8000')

        self.assertIn('visor_docker_sessionid', response.cookies)
        self.assertEqual(self.client.cookies['sessionid'].value, 'other-application-session')
        self.assertEqual(self.client.cookies['visor_sessionid'].value, 'native-visor-session')

    def test_callback_requires_valid_state(self):
        response = self.client.get(reverse('auth:github-oauth-callback'), {'code': 'code', 'state': 'bad'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['detail'], 'Invalid GitHub OAuth state')

    @patch('users.views.github_callback_view.exchange_code_for_token_data')
    def test_invalid_state_preserves_the_pending_login_and_does_not_exchange_code(self, exchange_code):
        session = self.client.session
        session[GITHUB_OAUTH_STATE_SESSION_KEY] = 'valid-state'
        session.save()

        for query in ({'state': 'wrong-state'}, {}, {'state': 'é'}):
            with self.subTest(query=query):
                response = self.client.get(reverse('auth:github-oauth-callback'), {'code': 'code', **query})
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(self.client.session[GITHUB_OAUTH_STATE_SESSION_KEY], 'valid-state')
                self.assertIn('no-store', response['Cache-Control'])
        exchange_code.assert_not_called()

    def test_older_callback_does_not_invalidate_a_newer_login(self):
        first = self.client.get(reverse('auth:github-oauth-login'), HTTP_HOST='localhost:8000')
        first_state = parse_qs(urlparse(first['Location']).query)['state'][0]
        second = self.client.get(reverse('auth:github-oauth-login'), HTTP_HOST='localhost:8000')
        second_state = parse_qs(urlparse(second['Location']).query)['state'][0]

        rejected = self.client.get(reverse('auth:github-oauth-callback'), {'state': first_state, 'error': 'access_denied'})
        self.assertEqual(rejected.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.session[GITHUB_OAUTH_STATE_SESSION_KEY], second_state)

        accepted = self.client.get(reverse('auth:github-oauth-callback'), {'state': second_state, 'error': 'access_denied'})
        self.assertEqual(accepted.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(accepted.json()['detail'], 'access_denied')

    def test_matching_state_can_only_be_used_once(self):
        session = self.client.session
        session[GITHUB_OAUTH_STATE_SESSION_KEY] = 'state'
        session.save()
        query = {'state': 'state', 'error': 'access_denied'}

        first = self.client.get(reverse('auth:github-oauth-callback'), query)
        replay = self.client.get(reverse('auth:github-oauth-callback'), query)
        self.assertEqual(first.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(replay.status_code, status.HTTP_403_FORBIDDEN)

    def test_callback_handles_github_error_response(self):
        session = self.client.session
        session[GITHUB_OAUTH_STATE_SESSION_KEY] = 'state'
        session.save()

        response = self.client.get(
            reverse('auth:github-oauth-callback'),
            {'error': 'access_denied', 'error_description': 'Denied', 'state': 'state'},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'Denied')

    @patch('users.views.github_callback_view.fetch_github_emails')
    @patch('users.views.github_callback_view.fetch_github_user')
    @patch('users.views.github_callback_view.exchange_code_for_token_data')
    def test_callback_creates_user_and_redirects_with_tokens(self, exchange_code, fetch_user, fetch_emails):
        exchange_code.return_value = {
            'access_token': 'github-token',
            'refresh_token': 'github-refresh-token',
            'expires_in': 28800,
            'refresh_token_expires_in': 15897600,
        }
        fetch_user.return_value = {
            'id': 123,
            'login': 'octocat',
            'name': 'Octo Cat',
            'email': None,
            'avatar_url': 'https://avatars.githubusercontent.com/u/123',
        }
        fetch_emails.return_value = [
            {'email': 'secondary@example.com', 'primary': False, 'verified': True},
            {'email': 'octocat@example.com', 'primary': True, 'verified': True},
        ]
        session = self.client.session
        session[GITHUB_OAUTH_STATE_SESSION_KEY] = 'state'
        session.save()

        response = self.client.get(reverse('auth:github-oauth-callback'), {'code': 'code', 'state': 'state'})

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        location = urlparse(response['Location'])
        self.assertEqual(f'{location.scheme}://{location.netloc}{location.path}', 'http://localhost:3000/login')
        self.assertEqual(set(parse_qs(location.query)), {'access', 'refresh'})
        self.assertNotIn('github-token', response['Location'])
        self.assertIn('no-store', response['Cache-Control'])

        user = User.objects.get(github_id='123')
        self.assertEqual(user.username, 'octocat')
        self.assertEqual(user.name, 'Octo Cat')
        self.assertEqual(user.email, 'octocat@example.com')
        self.assertEqual(user.access_token, 'github-token')
        self.assertEqual(user.github_refresh_token, 'github-refresh-token')
        self.assertIsNotNone(user.github_access_token_expires_at)
        self.assertIsNotNone(user.github_refresh_token_expires_at)

    @patch('users.views.github_callback_view.fetch_github_emails')
    @patch('users.views.github_callback_view.fetch_github_user')
    @patch('users.views.github_callback_view.exchange_code_for_token_data')
    def test_callback_updates_existing_user(self, exchange_code, fetch_user, fetch_emails):
        User.objects.create_user(github_id='123', username='old', email='old@example.com')
        exchange_code.return_value = {'access_token': 'new-token'}
        fetch_user.return_value = {
            'id': 123,
            'login': 'new-login',
            'name': 'New Name',
            'email': 'profile@example.com',
            'avatar_url': 'https://avatars.githubusercontent.com/u/123',
        }
        fetch_emails.return_value = []
        session = self.client.session
        session[GITHUB_OAUTH_STATE_SESSION_KEY] = 'state'
        session.save()

        response = self.client.get(reverse('auth:github-oauth-callback'), {'code': 'code', 'state': 'state'})

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        user = User.objects.get(github_id='123')
        self.assertEqual(user.username, 'new-login')
        self.assertEqual(user.email, 'profile@example.com')
        self.assertEqual(user.access_token, 'new-token')
