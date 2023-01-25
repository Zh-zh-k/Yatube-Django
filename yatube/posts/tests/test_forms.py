import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
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
            content_type='image/gif')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Проверка добавления поста и редиректа после отправки формы
        создания"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': self.post.image
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:profile',
                                               kwargs={'username': self.user}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(text='Тестовый текст',
                                group=self.group.id,
                                author=self.post.author).exists()
        )

    def test_edit_post(self):
        """Проверка редиректа и сохранения количества постов после отправки
        формы редактирования"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Другой тестовый текст',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}),
            is_edit=True,
            data=form_data,
        )
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                text='Другой тестовый текст',
                group=self.group.id,
                author=self.post.author
            ).exists()
        )

    def test_comment_added(self):
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'author': self.post.author,
            'post': self.post
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(text='Тестовый текст',
                                   post=self.post,
                                   author=self.post.author).exists()
        )
