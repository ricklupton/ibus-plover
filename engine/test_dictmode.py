import unittest
from plover.steno import Stroke, normalize_steno
from dictmode import DictMode

def stroke(s):
    keys = []
    on_left = True
    for k in s:
        if k in 'EU*-':
            on_left = False
        if k == '-': 
            continue
        elif k == '*': 
            keys.append(k)
        elif on_left: 
            keys.append(k + '-')
        else:
            keys.append('-' + k)
    return Stroke(keys)


class MockEngine:
    def __init__(self):
        self.message = ''
        self.candidate_list = []

    def get_current_word(self):
        return 'lastword'

    def show_message_list(self, message=None, values=None):
        if message is not None:
            self.message = message
        if values is not None:
            self.candidate_list = values


class MockDictionary(dict):
    def __init__(self):
        self.reverse_lookup_result = []

    def reverse_lookup(self, value):
        assert value == 'lastword'
        return self.reverse_lookup_result

    def set(self, key, value):
        self[key] = value


# This is arbitrary
SPECIAL = stroke('HAUF')


class DictModeTestCase(unittest.TestCase):
    def assertHandled(self, value):
        self.assertTrue(value)
    def assertUnhandled(self, value):
        self.assertFalse(value)

    def setUp(self):
        self.engine = MockEngine()
        self.dictionary = MockDictionary()
        options = dict(stroke=SPECIAL)
        self.dictmode = DictMode(self.engine, self.dictionary, options)


class DictMode_Basic_TestCase(DictModeTestCase):
    def test_most_strokes_not_handled(self):
        # Most strokes are not handled and pass through to steno engine
        self.assertUnhandled(self.dictmode.handle_stroke(stroke('KA-T')))

    def test_mode_activation(self):
        # Activate dict mode with special stroke
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))

        # * stroke exits (but is captured)
        self.assertHandled(self.dictmode.handle_stroke(stroke('*')))

        # After exiting strokes are not handled
        self.assertUnhandled(self.dictmode.handle_stroke(stroke('KA-T')))

    def test_add_to_dictionary(self):
        # Activate dict mode
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))

        # Type a few strokes
        self.assertHandled(self.dictmode.handle_stroke(stroke('KA-T')))
        self.assertHandled(self.dictmode.handle_stroke(stroke('TKO-G')))

        # Finish with special stroke - should call dictionary add
        self.assertEqual(self.dictionary.items(), [])
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))
        self.assertEqual(self.dictionary.items(),
                         [(('KAT', 'TKOG'), 'lastword')])

    def test_does_not_add_to_dictionary_if_no_strokes(self):
        # Activate dict mode and finish immediately - should do
        # nothing
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))
        self.assertEqual(self.dictionary.items(), [])

    def test_correcting_strokes_then_adding(self):
        # Activate dict mode
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))

        # Type a few strokes with a correction
        self.assertHandled(self.dictmode.handle_stroke(stroke('KA-T')))
        self.assertHandled(self.dictmode.handle_stroke(stroke('TKO-G')))
        self.assertHandled(self.dictmode.handle_stroke(stroke('*')))
        self.assertHandled(self.dictmode.handle_stroke(stroke('HREURB')))

        # Finish with special stroke - should call dictionary add
        self.assertEqual(self.dictionary.items(), [])
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))
        self.assertEqual(self.dictionary.items(),
                         [(('KAT', 'HREURB'), 'lastword')])

    def test_cancel_without_adding(self):
        # Activate dict mode
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))

        # Type a few strokes
        self.assertHandled(self.dictmode.handle_stroke(stroke('KA-T')))
        self.assertHandled(self.dictmode.handle_stroke(stroke('TKO-G')))

        # Type * to undo and exit
        self.assertHandled(self.dictmode.handle_stroke(stroke('*')))
        self.assertHandled(self.dictmode.handle_stroke(stroke('*')))
        self.assertHandled(self.dictmode.handle_stroke(stroke('*')))

        # After exiting, strokes are not handled, no word was added
        self.assertEqual(self.dictionary.items(), [])
        self.assertUnhandled(self.dictmode.handle_stroke(stroke('KA-T')))
        self.assertEqual(self.dictionary.items(), [])


class DictMode_VisualFeedback_TestCase(DictModeTestCase):
    def test_it_shows_existing_translations(self):
        self.dictionary.reverse_lookup_result = [
            ('HRAFT', 'WORD'), ('WHRAFTD',)]

        # Activate dict mode: should have asked engine to show
        # existing translations
        self.assertEqual(self.engine.message, '')
        self.assertEqual(self.engine.candidate_list, [])
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))
        self.assertEqual(self.engine.message, 'Definitions for "lastword":')
        self.assertEqual(self.engine.candidate_list,
                         ['HRAFT/WORD', 'WHRAFTD'])

    def test_it_does_not_show_missing_translations(self):
        self.dictionary.reverse_lookup_result = []

        # Activate dict mode: should have asked engine to show
        # that there are no existing definitions
        self.assertEqual(self.engine.message, '')
        self.assertEqual(self.engine.candidate_list, [])
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))
        self.assertEqual(self.engine.message, '(no definitions for "lastword")')
        self.assertEqual(self.engine.candidate_list, [])

    def test_it_updates_with_new_strokes(self):
        # Activate dict mode and type some strokes
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))

        self.assertHandled(self.dictmode.handle_stroke(stroke('KA-T')))
        self.assertEqual(self.engine.message, 'New definition for "lastword":')
        self.assertEqual(self.engine.candidate_list, ['KAT'])

        self.assertHandled(self.dictmode.handle_stroke(stroke('TKO-G')))
        self.assertEqual(self.engine.message, 'New definition for "lastword":')
        self.assertEqual(self.engine.candidate_list, ['KAT/TKOG'])

        self.assertHandled(self.dictmode.handle_stroke(stroke('*')))
        self.assertEqual(self.engine.message, 'New definition for "lastword":')
        self.assertEqual(self.engine.candidate_list, ['KAT'])

        self.assertHandled(self.dictmode.handle_stroke(stroke('*')))
        self.assertEqual(self.engine.message, 'New definition for "lastword":')
        self.assertEqual(self.engine.candidate_list, [''])

    def test_it_clears_message_when_exiting(self):
        # Activate dict mode and then exit
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))
        self.assertHandled(self.dictmode.handle_stroke(stroke('*')))
        self.assertEqual(self.engine.message, '')
        self.assertEqual(self.engine.candidate_list, [])

    def test_it_clears_message_when_finishing(self):
        # Activate dict mode and type a few strokes, then finish
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))
        self.assertHandled(self.dictmode.handle_stroke(stroke('KA-T')))
        self.assertHandled(self.dictmode.handle_stroke(stroke('TKO-G')))
        self.assertHandled(self.dictmode.handle_stroke(SPECIAL))
        self.assertEqual(self.engine.message, '')
        self.assertEqual(self.engine.candidate_list, [])


if __name__ == '__main__':
    unittest.main()
