from django.test import TestCase
from test_whoosh_app.models import Post


class SimpleTest(TestCase):
    def setUp(self):
        Post.objects.create(
            title='first post',
            body='This is my very first post ever in the world!'
        )
        Post.objects.create(
            title='second post',
            body='This is now the second post that I have indexed!'
        )
        Post.objects.create(
            title='third post',
            body='Whoah'
        )
    
    def test_query(self):
        self.assertEqual(
            Post.objects.query('title', 'first'),
            Post.objects.filter(title='first post')
        )
        self.assertEqual(
            Post.objects.query('title', 'post'), Post.objects.all()
        )