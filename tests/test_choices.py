from django.test import TestCase

from terracommon.terra.helpers import Choices

MY_CHOICES = Choices(
   ('ONE', 1, u'One for the money'),
   ('TWO', 2, u'Two for the show'),
   ('THREE', 3, u'Three to get ready'),
)
MY_CHOICES.add_subset("ODD", ("ONE", "THREE"))


class ChoicesTests(TestCase):
    """
    Testing the choices
    """
    def test_simple_choice(self):
        self.assertEqual(MY_CHOICES.CHOICES,
                         ((1, u"One for the money"),
                          (2, u"Two for the show"),
                          (3, u"Three to get ready"),))
        self.assertEqual(MY_CHOICES.CHOICES_DICT,
                         {
                             1: u'One for the money',
                             2: u'Two for the show',
                             3: u'Three to get ready'
                         })
        self.assertEqual(MY_CHOICES.REVERTED_CHOICES_DICT,
                         {
                            u'One for the money': 1,
                            u'Three to get ready': 3,
                            u'Two for the show': 2
                         })

    def test__contains__(self):
        self.failUnless(MY_CHOICES.ONE in MY_CHOICES)

    def test__iter__(self):
        self.assertEqual([k for k, v in MY_CHOICES], [1, 2, 3])

    def test_unique_values(self):
        self.assertRaises(ValueError, Choices,
                          ('TWO', 4, u'Deux'), ('FOUR', 4, u'Quatre'))

    def test_unique_constants(self):
        self.assertRaises(ValueError, Choices,
                          ('TWO', 2, u'Deux'), ('TWO', 4, u'Quatre'))

    def test_const_choice(self):
        self.assertEqual(MY_CHOICES.CONST_CHOICES,
                         (("ONE", u"One for the money"),
                          ("TWO", u"Two for the show"),
                          ("THREE", u"Three to get ready"),))

    def test_value_to_const(self):
        self.assertEqual(MY_CHOICES.VALUE_TO_CONST,
                         {1: "ONE", 2: "TWO", 3: "THREE"})

    def test_add_should_add_in_correct_order(self):
        SOME_CHOICES = Choices(
           ('ONE', 1, u'One'),
           ('TWO', 2, u'Two'),
        )
        OTHER_CHOICES = Choices(
           ('THREE', 3, u'Three'),
           ('FOUR', 4, u'Four'),
        )
        # Adding a choices to choices
        tup = SOME_CHOICES + OTHER_CHOICES
        self.assertEqual(tup, ((1, 'One'), (2, 'Two'),
                               (3, 'Three'), (4, 'Four')))

        # Adding a tuple to choices
        tup = SOME_CHOICES + ((3, 'Three'), (4, 'Four'))
        self.assertEqual(tup, ((1, 'One'), (2, 'Two'),
                               (3, 'Three'), (4, 'Four')))

        """Adding a choices to tuple => do not work; is it possible to
           emulate it?
            tup = ((1, 'One'), (2, 'Two')) + OTHER_CHOICES
            self.assertEqual(tup, ((1, 'One'), (2, 'Two'),
                                   (3, 'Three'), (4, 'Four')))
        """

    def test_retrocompatibility(self):
        MY_CHOICES = Choices(
           ('TWO', 2, u'Deux'),
           ('FOUR', 4, u'Quatre'),
           name="EVEN"
        )
        MY_CHOICES.add_choices("ODD",
                               ('ONE', 1, u'Un'),
                               ('THREE', 3, u'Trois'),)
        self.assertEqual(MY_CHOICES.CHOICES, ((2, u'Deux'), (4, u'Quatre'),
                                              (1, u'Un'), (3, u'Trois')))
        self.assertEqual(MY_CHOICES.ODD, ((1, u'Un'), (3, u'Trois')))
        self.assertEqual(MY_CHOICES.EVEN, ((2, u'Deux'), (4, u'Quatre')))


# Needed for Subset tests
MY_CHOICES.add_subset("ODD_BIS", ("ONE", "THREE"))


class SubsetTests(TestCase):

    def test_basic(self):
        self.assertEqual(MY_CHOICES.ODD, ((1, u'One for the money'),
                                          (3, u'Three to get ready')))

    def test__contains__(self):
        self.failUnless(MY_CHOICES.ONE in MY_CHOICES.ODD)

    def test__eq__(self):
        self.assertEqual(MY_CHOICES.ODD, ((1, u'One for the money'),
                                          (3, u'Three to get ready')))
        self.assertEqual(MY_CHOICES.ODD, MY_CHOICES.ODD_BIS)
