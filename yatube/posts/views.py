from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User
from .utils import pages


def index(request):
    '''Принимает запрос, возвращает главную страницу'''
    template = 'posts/index.html'
    posts = Post.objects.select_related('author', 'group')
    page_obj = pages(request, posts)
    context = {
        'page_obj': page_obj
    }
    return render(request, template, context)


def group_posts(request, slug):
    '''Принимает запрос и слаг, возвращает страницу группы'''
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = pages(request, posts)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    '''Принимает запрос и имя пользователя, возвращает страницу пользователя'''
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    page_obj = pages(request, posts)
    posts_number = posts.count()
    if request.user.is_authenticated:
        following = Follow.objects.filter(user=request.user,
                                          author=author).exists()
    else:
        following = False
    context = {
        'page_obj': page_obj,
        'author': author,
        'posts_number': posts_number,
        'following': following
    }
    return render(request, template, context)


def post_detail(request, post_id):
    '''Принимает запрос и id поста, возвращает страницу поста'''
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, id=post_id)
    author = post.author
    posts_count = author.posts.filter(author=author).count()
    form = CommentForm(request.POST or None)
    comments = Comment.objects.filter(post=post)
    context = {
        'post': post,
        'posts_number': posts_count,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    if request.method == 'POST':
        form = PostForm(request.POST or None, files=request.FILES or None)
        if form.is_valid():
            form.instance.author = request.user
            form.save()
            return redirect('posts:profile', username=request.user)
    form = PostForm(request.POST or None, files=request.FILES or None)
    context = {
        'form': form,
        'title': 'Новый пост',
    }
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, id=post_id)
    if request.user == post.author:
        if request.method == 'POST':
            form = PostForm(request.POST or None,
                            files=request.FILES or None,
                            instance=post)
            if form.is_valid():
                form.save()
                return redirect('posts:post_detail', post_id)
        form = PostForm(
            request.POST or None,
            files=request.FILES or None,
            instance=post)
        context = {
            'title': 'Редактировать запись',
            'form': form,
            'is_edit': True,
            'post': post
        }
        return render(request, template, context)
    else:
        return redirect('posts:post_detail', post_id)


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
    template = 'posts/follow.html'
    posts = Post.objects.filter(
        author__following__user=request.user,
    ).select_related('author', 'group')
    page_obj = pages(request, posts)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    user = get_object_or_404(User, username=request.user)
    author = get_object_or_404(User, username=username)
    if user == author:
        return redirect('posts:profile', username=username)
    Follow.objects.get_or_create(author=author, user=request.user)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=username)
