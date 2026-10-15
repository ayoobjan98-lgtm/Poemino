from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from MakerPom.models import CreatPom
from MakerPom.services import build_poem_queryset, get_filter_params


class PoemSearchFilterServiceTest(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.author = User.objects.create_user(username='hafez', password='test')
        self.author2 = User.objects.create_user(username='saadi', password='test')

        self.p1 = CreatPom.objects.create(
            name='Spring',
            text='Love is all around',
            author=self.author,
            status='a',
            poem_type='ghazal',
            created_at=timezone.now() - timedelta(days=10),
            edited_at=timezone.now() - timedelta(days=5),
        )
        self.p2 = CreatPom.objects.create(
            name='Spring of the Heart',
            text='A friend in need',
            author=self.author,
            status='a',
            poem_type='ghazal',
            created_at=timezone.now() - timedelta(days=8),
            edited_at=timezone.now() - timedelta(days=4),
        )
        self.p3 = CreatPom.objects.create(
            name='Masnavi',
            text='Love is the answer',
            author=self.author2,
            status='a',
            poem_type='masnavi',
            created_at=timezone.now() - timedelta(days=6),
            edited_at=timezone.now() - timedelta(days=2),
        )

    def test_search_by_author(self):
        params = {'q': 'hafez'}
        qs = build_poem_queryset(CreatPom.objects.all(), params)
        self.assertEqual(set(qs), {self.p1, self.p2})

    def test_search_by_title_partial(self):
        params = {'q': 'spring'}
        qs = build_poem_queryset(CreatPom.objects.all(), params)
        self.assertIn(self.p1, qs)
        self.assertIn(self.p2, qs)

    def test_search_by_text_multiple(self):
        params = {'q': 'love'}
        qs = build_poem_queryset(CreatPom.objects.all(), params)
        self.assertEqual(set(qs), {self.p1, self.p3})

    def test_filter_author(self):
        params = {'author': 'hafez'}
        qs = build_poem_queryset(CreatPom.objects.all(), params)
        self.assertEqual(set(qs), {self.p1, self.p2})

    def test_filter_poem_type(self):
        params = {'poem_type': 'ghazal'}
        qs = build_poem_queryset(CreatPom.objects.all(), params)
        self.assertEqual(set(qs), {self.p1, self.p2})

    def test_filter_created_range(self):
        params = {
            'created_from': (timezone.now() - timedelta(days=11)).strftime('%Y-%m-%d'),
            'created_to': (timezone.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        }
        qs = build_poem_queryset(CreatPom.objects.all(), params)
        self.assertIn(self.p1, qs)
        self.assertIn(self.p2, qs)
        self.assertNotIn(self.p3, qs)

    def test_search_plus_filters(self):
        params = {'q': 'love', 'poem_type': 'ghazal', 'author': 'hafez'}
        qs = build_poem_queryset(CreatPom.objects.all(), params)
        self.assertEqual(set(qs), {self.p1})

    def test_no_duplicate_results(self):
        # Create a poem that matches both title and text to test distinct
        p4 = CreatPom.objects.create(
            name='Love',
            text='Love is everywhere',
            author=self.author,
            status='a',
            poem_type='ghazal',
            created_at=timezone.now() - timedelta(days=3),
            edited_at=timezone.now() - timedelta(days=1),
        )
        params = {'q': 'love'}
        qs = build_poem_queryset(CreatPom.objects.all(), params)
        self.assertEqual(len(qs), 3)  # p1, p3, p4 all have "love" in text, p4 also in name