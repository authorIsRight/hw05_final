import shutil
import tempfile


from django import forms
from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )
        cls.group2 = Group.objects.create(
            title='Тестовое название группы2',
            slug='test-slug2',
            description='Тестовое описание2',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # пробуем отчистить кэш, чтобы тесты работали
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def check_post_info(self, context):
        with self.subTest(context=context):
            self.assertEqual(context.text, self.post.text)
            self.assertEqual(context.pub_date, self.post.pub_date)
            self.assertEqual(context.author, self.post.author)
            self.assertEqual(context.group.id, self.post.group.id)
            self.assertEqual(context.image, self.post.image)

    def test_post_exists_in_index_group_profile(self):
        """Пост на главной, странице группы и на профиле."""
        post = PostPagesTests.post
        reverses_filters_dict = {
            reverse('posts:index'): Post.objects.all(),
            reverse('posts:group_list', kwargs={'slug': post.group.slug}):
                Post.objects.filter(group=post.group),
            reverse(
                'posts:profile',
                kwargs={'username': post.author.username}
            ): Post.objects.filter(author=post.author),
        }
        for reverse_name, filters in reverses_filters_dict.items():
            with self.subTest(reverse_name=reverse_name):
                self.assertTrue(filters.exists())

    def test_post_does_not_exist_in_another_group(self):
        """В иной группе быть не должно"""
        post = PostPagesTests.post
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group2.slug})
        )
        self.assertNotIn(post, response.context.get('page_obj'))
        group2 = response.context.get('group')
        self.assertEqual(group2, PostPagesTests.group2)

    def test_forms_show_correct(self):
        """Проверка коректности формы."""
        context = {
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.id, }),
        }
        for reverse_page in context:
            with self.subTest(reverse_page=reverse_page):
                response = self.authorized_client.get(reverse_page)
                self.assertIsInstance(
                    response.context['form'].fields['text'],
                    forms.fields.CharField)
                self.assertIsInstance(
                    response.context['form'].fields['group'],
                    forms.fields.ChoiceField)
                self.assertIsInstance(
                    response.context['form'].fields['image'],
                    forms.fields.ImageField)

    def test_index_page_show_correct_context(self):
        """Шаблон index.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_post_info(response.context['page_obj'][0])

    def test_groups_page_show_correct_context(self):
        """Шаблон group_list.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['group'], self.group)
        self.check_post_info(response.context['page_obj'][0])

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}))
        self.assertEqual(response.context['author'], self.user)
        self.check_post_info(response.context['page_obj'][0])

    def test_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}))
        self.check_post_info(response.context['post'])

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.post.author.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            ): 'includes/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_cashe(self):
        """Проверка роботоспособности кэша"""
        post = Post.objects.create(
            text='Тестируем кэш',
            author=self.user
        )
        response = self.authorized_client.get(
            reverse('posts:index')
        ).content
        post.delete()

        response_cashed = self.authorized_client.get(
            reverse('posts:index')
        ).content
        # закашерировано, шуд игнор делишн
        self.assertEqual(response_cashed, response)
        # очистим, чтобы не обращалось к кэшу
        cache.clear()

        non_cashed_response = self.authorized_client.get(
            reverse('posts:index')
        ).content

        self.assertNotEqual(non_cashed_response, response)
        self.assertNotEqual(non_cashed_response, response_cashed)
