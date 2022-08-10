from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache


from posts.models import Group, Post, Comment

User = get_user_model()


class PostCreateFormTests(TestCase):
    """ Тест форм сайта."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='aBoyHasNoName')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.user = PostCreateFormTests.user
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_authorized_user_create_comment(self):
        """Проверка создания коммента авторизированным пользщователем"""
        comments_count = Comment.objects.count()
        post = Post.objects.create(
            text='Тест Текст пост',
            author=self.user)
        form_data = {'text': 'Тестовый коммент'}
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=True)
        comment = Comment.objects.latest('id')
        # появился новый коммент на странице поста
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post_id, post.id)
        self.assertRedirects(
            response, reverse('posts:post_detail', args={post.id}))

    def test_nonauthorized_user_create_comment(self):
        """Проверка создания коммента не авторизированным пользователем."""
        comments_count = Comment.objects.count()
        post = Post.objects.create(
            text='Тест Текст пост',
            author=self.user)
        form_data = {'text': 'Тестовый коммент'}
        response = self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=True)
        redirect = reverse('login') + '?next=' + reverse(
            'posts:add_comment', kwargs={'post_id': post.id})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # не появился на странице поста
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(response, redirect)
