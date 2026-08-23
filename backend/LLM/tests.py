from django.contrib.auth.models import User
from django.test import Client, SimpleTestCase, TestCase

from LLM.models import APIKey, Model, UserAPIKey
from LLM.session_auth import GROUP_ADMIN, GROUP_USER, get_user_role, set_user_role
from LLM.utils import (
    NoActiveModelError,
    ModelTypeMismatchError,
    extract_ollama_message_parts,
    normalize_thinking_input,
    resolve_requested_model,
    resolve_think_value,
    think_value_for_storage,
)


class ThinkingModeTests(SimpleTestCase):
    def test_normalize_default_values(self):
        self.assertIsNone(normalize_thinking_input('default'))
        self.assertIsNone(normalize_thinking_input('auto'))
        self.assertIsNone(normalize_thinking_input(None))

    def test_normalize_levels(self):
        self.assertEqual(normalize_thinking_input('low'), 'low')
        self.assertEqual(normalize_thinking_input('MEDIUM'), 'medium')
        self.assertEqual(normalize_thinking_input('high'), 'high')

    def test_normalize_boolean_aliases(self):
        self.assertEqual(normalize_thinking_input(True), 'true')
        self.assertEqual(normalize_thinking_input(False), 'false')
        self.assertEqual(normalize_thinking_input('enabled'), 'true')
        self.assertEqual(normalize_thinking_input('disabled'), 'false')
        self.assertEqual(normalize_thinking_input('none'), 'false')

    def test_normalize_invalid_value(self):
        with self.assertRaises(ValueError):
            normalize_thinking_input('turbo')

    def test_resolve_request_thinking_levels(self):
        self.assertEqual(resolve_think_value('low', 'default'), 'low')
        self.assertEqual(resolve_think_value('high', 'default'), 'high')
        self.assertIsNone(resolve_think_value('default', 'default'))

    def test_resolve_model_default(self):
        self.assertIsNone(resolve_think_value(None, 'default'))
        self.assertIsNone(resolve_think_value(None, 'auto'))
        self.assertTrue(resolve_think_value(None, 'enabled'))
        self.assertFalse(resolve_think_value(None, 'disabled'))
        self.assertEqual(resolve_think_value(None, 'low'), 'low')

    def test_request_overrides_model_default(self):
        self.assertEqual(resolve_think_value('high', 'low'), 'high')

    def test_think_value_for_storage(self):
        self.assertIsNone(think_value_for_storage(None))
        self.assertEqual(think_value_for_storage(True), 'true')
        self.assertEqual(think_value_for_storage(False), 'false')
        self.assertEqual(think_value_for_storage('medium'), 'medium')


class ModelResolutionTests(TestCase):
    def setUp(self):
        self.active_chat = Model.objects.create(
            name='active-chat',
            model_path='active-chat',
            model_type='chat',
            provider='ollama',
            is_active=True,
        )
        self.inactive_chat = Model.objects.create(
            name='inactive-chat',
            model_path='inactive-chat',
            model_type='chat',
            provider='ollama',
            is_active=False,
        )
        self.default_chat = Model.objects.create(
            name='default-chat',
            model_path='default-chat',
            model_type='chat',
            provider='ollama',
            is_active=True,
            is_default=True,
        )

    def test_uses_requested_active_model(self):
        model, routed_from = resolve_requested_model('active-chat', 'chat')
        self.assertEqual(model.name, 'active-chat')
        self.assertIsNone(routed_from)

    def test_routes_inactive_model_to_default(self):
        model, routed_from = resolve_requested_model('inactive-chat', 'chat')
        self.assertEqual(model.name, 'default-chat')
        self.assertEqual(routed_from, 'inactive-chat')

    def test_routes_missing_model_to_default(self):
        model, routed_from = resolve_requested_model('missing-chat', 'chat')
        self.assertEqual(model.name, 'default-chat')
        self.assertEqual(routed_from, 'missing-chat')

    def test_routes_missing_model_name_to_default(self):
        model, routed_from = resolve_requested_model(None, 'chat')
        self.assertEqual(model.name, 'default-chat')
        self.assertIsNone(routed_from)

    def test_wrong_model_type_raises(self):
        embedding = Model.objects.create(
            name='embed-model',
            model_path='embed-model',
            model_type='embedding',
            provider='ollama',
            is_active=True,
        )
        with self.assertRaises(ModelTypeMismatchError):
            resolve_requested_model('embed-model', 'chat')

    def test_no_active_models_raises(self):
        Model.objects.all().update(is_active=False)
        with self.assertRaises(NoActiveModelError):
            resolve_requested_model('inactive-chat', 'chat')


class OllamaMessageExtractionTests(SimpleTestCase):
    def test_extract_from_dict(self):
        content, thinking = extract_ollama_message_parts({
            'content': 'answer',
            'thinking': 'reasoning',
        })
        self.assertEqual(content, 'answer')
        self.assertEqual(thinking, 'reasoning')

    def test_extract_content_only(self):
        content, thinking = extract_ollama_message_parts({'content': 'answer'})
        self.assertEqual(content, 'answer')
        self.assertEqual(thinking, '')


class UserGroupSignalTests(TestCase):
    def test_new_user_gets_user_group(self):
        user = User.objects.create_user(username='alice', password='pass')
        self.assertTrue(user.groups.filter(name=GROUP_USER).exists())
        self.assertFalse(user.groups.filter(name=GROUP_ADMIN).exists())

    def test_superuser_gets_admin_group(self):
        user = User.objects.create_superuser(username='admin1', password='pass', email='a@b.c')
        self.assertTrue(user.groups.filter(name=GROUP_ADMIN).exists())
        self.assertEqual(get_user_role(user), GROUP_ADMIN)


class InternalAPITests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.admin = User.objects.create_user(username='adminuser', password='adminpass')
        set_user_role(self.admin, GROUP_ADMIN)

        self.regular = User.objects.create_user(username='regular', password='userpass')
        self.admin_key = APIKey.objects.create(name='admin-key')
        self.user_key = APIKey.objects.create(name='user-key')
        UserAPIKey.objects.create(user=self.regular, api_key=self.user_key)

        self.model = Model.objects.create(
            name='test-model',
            model_path='test-model',
            model_type='chat',
            provider='ollama',
            is_active=True,
        )

    def _login(self, username, password):
        csrf = self.client.get('/internal/auth/csrf')
        token = csrf.json()['csrfToken']
        return self.client.post(
            '/internal/auth/login',
            data={'username': username, 'password': password},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )

    def test_health_is_public(self):
        response = self.client.get('/internal/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_public_stats(self):
        response = self.client.get('/internal/public/stats')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_requests', response.json())

    def test_login_and_me(self):
        login_response = self._login('regular', 'userpass')
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()['user']['role'], 'user')

        me_response = self.client.get('/internal/auth/me')
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()['username'], 'regular')

    def test_user_sees_only_owned_keys(self):
        self._login('regular', 'userpass')
        response = self.client.get('/internal/me/keys')
        self.assertEqual(response.status_code, 200)
        key_ids = [key['id'] for key in response.json()['keys']]
        self.assertEqual(key_ids, [self.user_key.id])

    def test_user_cannot_access_admin_models(self):
        self._login('regular', 'userpass')
        response = self.client.get('/internal/admin/models')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_models(self):
        self._login('adminuser', 'adminpass')
        response = self.client.get('/internal/admin/models')
        self.assertEqual(response.status_code, 200)
        names = [model['name'] for model in response.json()['models']]
        self.assertIn('test-model', names)

    def test_admin_create_user_provisions_key(self):
        self._login('adminuser', 'adminpass')
        csrf = self.client.get('/internal/auth/csrf')
        token = csrf.json()['csrfToken']
        response = self.client.post(
            '/internal/admin/users',
            data={
                'username': 'newbie',
                'password': 'newbiepass',
                'role': 'user',
            },
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        newbie = User.objects.get(username='newbie')
        self.assertTrue(UserAPIKey.objects.filter(user=newbie).exists())

    def test_rate_limit_headers_on_v1_models(self):
        response = self.client.get(
            '/v1/models',
            HTTP_AUTHORIZATION=f'Bearer {self.user_key.key}',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('X-RateLimit-Limit-Minute', response)
        self.assertIn('X-RateLimit-Remaining-Minute', response)
        self.assertIn('X-RateLimit-Limit-Hour', response)
        self.assertIn('X-RateLimit-Remaining-Hour', response)

    def test_rate_limit_429_includes_retry_after(self):
        self.user_key.rate_limit_per_minute = 1
        self.user_key.save(update_fields=['rate_limit_per_minute'])
        from LLM.models import LLMRequest
        LLMRequest.objects.create(
            api_key=self.user_key,
            model=self.model,
            prompt='hello',
            status='completed',
        )
        response = self.client.get(
            '/v1/models',
            HTTP_AUTHORIZATION=f'Bearer {self.user_key.key}',
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['X-RateLimit-Remaining-Minute'], '0')
        self.assertIn('Retry-After', response)

    def test_user_requests_are_scoped_and_omit_prompt(self):
        from LLM.models import LLMRequest
        other_key = APIKey.objects.create(name='other')
        LLMRequest.objects.create(
            api_key=self.user_key,
            model=self.model,
            prompt='secret-owned',
            status='completed',
        )
        LLMRequest.objects.create(
            api_key=other_key,
            model=self.model,
            prompt='secret-other',
            status='completed',
        )
        self._login('regular', 'userpass')
        response = self.client.get('/internal/me/requests')
        self.assertEqual(response.status_code, 200)
        rows = response.json()['requests']
        self.assertEqual(len(rows), 1)
        self.assertNotIn('prompt', rows[0])
        self.assertNotIn('secret-owned', str(rows[0]))
