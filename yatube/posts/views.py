from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Group, Post, Follow

LIMIT_POSTS: int = 10

User = get_user_model()


# Главная страница
@cache_page(20, key_prefix="index_page")
def index(request):
    posts = Post.objects.all()
    # Если порядок сортировки определен в классе Meta модели,
    # запрос будет выглядить так:
    # post_list = Post.objects.all()
    # Показывать по 10 записей на странице.
    paginator = Paginator(posts, LIMIT_POSTS)
    # Из URL извлекаем номер запрошенной страницы - это значение параметра page
    page_number = request.GET.get('page')
    # Получаем набор записей для страницы с запрошенным номером
    page_obj = paginator.get_page(page_number)
    # Отдаем в словаре контекста
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, LIMIT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    paginator = Paginator(posts, LIMIT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    following = request.user.is_authenticated
    if following:
        following = author.following.filter(user=request.user).exists()
    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm()
    comments = post.comments.all()
    context = {
        'post': post,
        'comments': comments,
        'form': form
        # delete or include?
    }
    return render(request, 'includes/post_detail.html', context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    if request.method != 'POST':
        form = PostForm()
        context = {'form': form}
        return render(request, template, context)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    context = {'form': form}
    if form.is_valid():
        create_post = form.save(commit=False)
        create_post.author = request.user
        create_post.save()
        return redirect('posts:profile', request.user.username)
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """thank you, stackOverflow!:
мы имеем связь между объектами (а точнее таблицами в БД).
Post -> Author <-> Follow <-> User. Сначала ищется
пользователь с заданным именем. Для него ищутся объекты
в таблице Follow, которые на него ссылаются.
Далее для всех найденных записей в Follow ищутся
связанные с ними авторы. А далее все посты,
которые связанны с найденными авторами.
На уровне БД и SQL делается join всех этих таблиц
и фильтрация по идентификатору пользователя, который
берется из request.user."""
    posts = Post.objects.filter(
        author__following__user=request.user)
    paginator = Paginator(posts, LIMIT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(
            user=request.user,
            author=author
        )
    return redirect('posts:profile', author)


@login_required
def profile_unfollow(request, username):
    follower = get_object_or_404(
        Follow,
        user=request.user,
        author__username=username
    )
    follower.delete()
    return redirect('posts:profile', username)
