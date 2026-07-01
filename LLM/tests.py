from django.test import SimpleTestCase, TestCase

from LLM.models import Model
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
        self.assertEqual(resolve_think_value('low', None, 'default'), 'low')
        self.assertEqual(resolve_think_value('high', None, 'default'), 'high')
        self.assertIsNone(resolve_think_value('default', None, 'default'))

    def test_resolve_reasoning_effort_alias(self):
        self.assertEqual(resolve_think_value(None, 'medium', 'default'), 'medium')
        self.assertEqual(resolve_think_value(None, 'none', 'default'), False)

    def test_resolve_model_default(self):
        self.assertIsNone(resolve_think_value(None, None, 'default'))
        self.assertIsNone(resolve_think_value(None, None, 'auto'))
        self.assertTrue(resolve_think_value(None, None, 'enabled'))
        self.assertFalse(resolve_think_value(None, None, 'disabled'))
        self.assertEqual(resolve_think_value(None, None, 'low'), 'low')

    def test_request_overrides_model_default(self):
        self.assertEqual(resolve_think_value('high', None, 'low'), 'high')

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
