from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.core.cache import cache

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.auth = User.objects.create_user(username='test_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.auth,
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.auth)
        cache.clear()

    def test_urls_match_template(self):
        """HTML шаблоны."""
        # cleared cache so in setup so '/' would work
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.post.author}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'includes/post_detail.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            # страница 404 отдаст кастомный шаблон
            '/page404/': 'core/404.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_author.get(adress)
                self.assertTemplateUsed(response, template)

    def test_url_for_guest(self):
        """URL-адрес не доступен гостю."""
        templates_url_names = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.post.author}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.FOUND,
            'unexist.html': HTTPStatus.NOT_FOUND,
        }
        for template, status in templates_url_names.items():
            with self.subTest(status=status):
                response = self.guest_client.get(template)
                self.assertEqual(response.status_code, status)

    def test_url_for_user(self):
        """URL-адрес для зарегистрированного юзера и не автора."""
        templates_url_names = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.post.author}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.OK,
            'unexist.html': HTTPStatus.NOT_FOUND,
        }
        for template, status in templates_url_names.items():
            with self.subTest(status=status):
                response = self.authorized_client.get(template)
                self.assertEqual(response.status_code, status)

    def test_url_auth(self):
        """Для автора поста почти все доступно."""
        templates_url_names = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.post.author}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/edit/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
            'unexist.html': HTTPStatus.NOT_FOUND,
        }
        for template, status in templates_url_names.items():
            with self.subTest(status=status):
                response = self.authorized_author.get(template)
                self.assertEqual(response.status_code, status)
