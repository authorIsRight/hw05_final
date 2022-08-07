from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User

FIRST_PAGE = 10
SECOND_PAGE = 3


class PaginatorViewsTest(TestCase):
    """Тест пагинатора"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='help_me')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание',
        )
        posts = [Post(author=cls.user, group=cls.group, text='Тестовый пост № '
                 + str(i + 1))
                 for i in range(FIRST_PAGE + SECOND_PAGE)]
        # In views bulk_create нарушается порядок,
        # another approached is used in test_views
        Post.objects.bulk_create(posts)

    def setUp(self):
        self.guest_client = Client()

    def test_paginator(self):
        context = {
            reverse('posts:index'): FIRST_PAGE,
            reverse('posts:index') + '?page=2': SECOND_PAGE,
            reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            ): FIRST_PAGE,
            reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            ) + '?page=2': SECOND_PAGE,
            reverse(
                'posts:profile', kwargs={'username': 'help_me'}
            ): FIRST_PAGE,
            reverse(
                'posts:profile', kwargs={'username': 'help_me'}
            ) + '?page=2': SECOND_PAGE,
        }
        for reverse_page, pages_posts in context.items():
            with self.subTest(reverse_page=reverse_page):
                self.assertEqual(len(self.guest_client.get(
                    reverse_page).context.get('page_obj')), pages_posts)
