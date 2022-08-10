
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from django.test import Client, TestCase
from django.core.cache import cache

from ..models import Post, Follow


User = get_user_model()


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(
            username='author',
        )
        cls.follower = User.objects.create(
            username='follower',
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)

    def test_follow_on_user(self):
        """Проверка подписки на автора"""
        followers = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author}))
        follow = Follow.objects.all().latest('id')
        self.assertEqual(Follow.objects.count(), followers + 1)
        self.assertEqual(follow.user_id, self.follower.id)
        self.assertEqual(follow.author_id, self.author.id)

    def test_follow_on_user(self):
        """Проверка отписки от автора"""
        self.follower_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author}))
        followers = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author}))
        self.assertEqual(Follow.objects.count(), followers - 1)

    def test_post_visible_if_follower(self):
        """Пост появляются для подписчика"""
        post = Post.objects.create(
            author=self.author,
            text='follow Chubbyemu, he has cool channel on medicine'
        )
        self.follower_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author}))
        response = self.follower_client.get(
            reverse('posts:follow_index'))
        self.assertEqual(post, response.context['page_obj'][0])

    def test_post_not_showing_if_not_follower(self):
        """Пост не появляются у не подписчика"""
        post = Post.objects.create(
            author=self.author,
            text=str(f'{self.author} is tired')
        )
        self.follower_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author}))
        response = self.follower_client.get(
            reverse('posts:follow_index'))
        # убедимся, что все работает
        self.assertEqual(post, response.context['page_obj'][0])
        # отпишемся, больше не подписчик
        self.follower_client.post(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author}))
        response = self.follower_client.get(
            reverse('posts:follow_index'))
        self.assertNotIn(post, response.context['page_obj'])
