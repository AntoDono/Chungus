from django.test import SimpleTestCase

from LLM.utils import (
    normalize_thinking_input,
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
