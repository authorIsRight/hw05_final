import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache


from posts.models import Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    """ Тест форм сайта."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='aBoyHasNoName')
        cls.auth = User.objects.create_user(username='Neo')
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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = PostCreateFormTests.user
        self.auth = PostCreateFormTests.auth
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_not_author = Client()
        self.authorized_not_author.force_login(self.auth)

        cache.clear()

    def post_asserts(self, post, form_data):
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group_id, form_data['group'])

    def test_post_create(self):
        """Проверка создания поста."""
        posts_count = Post.objects.count()
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
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username})
        )

        self.assertEqual(Post.objects.count(), posts_count + 1)
        # неавторизованный пользователь пытается создать пост
        self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)

        post = Post.objects.latest('id')
        # call function to make some asserts
        self.post_asserts(post, form_data)
        self.assertEqual(post.image.name, 'posts/small.gif')

    def test_post_edit(self):
        """Проверка редактирования поста."""
        form_data = {
            'text': 'Тестовый текст1',
            'group': self.group.id,
        }
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        post = Post.objects.get(
            text=form_data['text'],
            group=form_data['group']
        )
        # call function to make some asserts
        self.post_asserts(post, form_data)

    def test_post_edit_by_other(self):
        """Проверка редактирования поста другим юзером."""
        form_data = {
            'text': 'Упс, что-то пошло не так',
            'group': self.group.id,
        }
        self.authorized_not_author.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        # thanks to Arsen for the help with the next row))
        post = Post.objects.get(id=self.post.id)
        # tried to change only text, should not be equal
        self.assertNotEqual(post.text, form_data['text'])
        # Group and author were not the subject to the change
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group_id, form_data['group'])
