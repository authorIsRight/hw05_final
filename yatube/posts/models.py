from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import UniqueConstraint

User = get_user_model()


class Group(models.Model):
    class Meta:
        ordering = ['-slug']

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(models.Model):
    class Meta:
        ordering = ['-pub_date']
        # added in 6 sprint (hope this will not ruin all)
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    text = models.TextField(
        'Текст поста',
        help_text='Введите текст поста'
    )
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='posts'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        related_name='posts',
        blank=True,
        null=True,
        verbose_name='Группа',
        help_text='Группа, к которой будет относиться пост'
    )

    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    def corrected_text(self):
        if not self.text:
            return "-пусто"
        return self.text
        """this allows to change blanks in the admin view"""
    corrected_text.short_description = 'text'

    def __str__(self):
        # выводим текст поста
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    text = models.TextField(
        verbose_name='Коммент'
    )
    created = models.DateTimeField(
        'Создан',
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created']

    def __str__(self):
        # выводим текст коммента
        return self.text[:15]


class Follow(models.Model):
    class Meta:
        ordering = ['-user']
        UniqueConstraint(name='follower_follows',
                         fields=['user', 'author'])

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='подписчик'
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name_plural = 'Подписки'
        verbose_name = 'Подписка'
