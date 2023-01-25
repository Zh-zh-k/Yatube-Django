import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Follow, Group, Post
from ..utils import NUM_OF_POSTS

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test_slug',
            description='Тестовое описание'
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
            text='Тестовый текст',
            group=cls.group,
            pub_date='Дата',
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_index_page_cache(self):
        """Проверка работы кэша на главной странице"""
        response_1 = self.authorized_client.get(reverse('posts:index'))
        Post.objects.get(id=self.post.id).delete()
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_1, response_3)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse('posts:group_posts',
                                             kwargs={'slug': self.group.slug}),
            'posts/profile.html': reverse('posts:profile',
                                          kwargs={'username': 'NoName'}),
            'posts/create_post.html': reverse('posts:post_create'),
            'posts/post_detail.html': reverse('posts:post_detail',
                                              kwargs={'post_id': self.post.id})
        }

        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_post(self, first_object):
        """Проверка контекста поста"""
        self.assertEqual(first_object.text, self.post.text,
                         'Не совпадает текст')
        self.assertEqual(first_object.author, self.user,
                         'Не совпадает автор')
        self.assertEqual(first_object.group, self.group,
                         'Не совпадает группа')
        self.assertEqual(first_object.image, self.post.image,
                         'Нет картинки')
        self.assertEqual(first_object.pub_date, self.post.pub_date,
                         'Не совпадает дата публикации')

    def text_index_page_show_correct_context(self):
        """Главная страница показывает нужный контекст"""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)

    def test_group_page_show_correct_context(self):
        """Страница группы показывает нужный контекст"""
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group.slug})
        )
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)
        self.assertEqual(response.context['group'], self.group)

    def test_profile_page_show_correct_context(self):
        """Страница профиля показывает нужный контекст"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'NoName'})
        )
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)
        self.assertEqual(response.context['author'], self.user)

    def test_post_detail_page_show_correct_context(self):
        """Страница поста показывает нужный контекст"""
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id})
        )
        first_object = response.context['post']
        self.check_post(first_object)

    def test_create_post_form_show_correct_context(self):
        """Страница создания поста показывает нужный контекст"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form = response.context.get('form')
                self.assertIsInstance(form, PostForm)

    def test_edit_post_form_show_correct_context(self):
        """Страница редактирования поста показывает нужный контекст"""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertTrue(response.context['is_edit'])

    def test_post_added_correctly(self):
        """Пост добавляется корректно"""
        post_new = Post.objects.create(text='Текст',
                                       author=self.user,
                                       group=self.group)
        response_index = self.authorized_client.get(reverse('posts:index'))
        response_group = self.authorized_client.get(
            reverse('posts:group_posts',
                    kwargs={'slug': f'{self.group.slug}'})
        )
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'})
        )
        response_follower = self.authorized_client.get(
            reverse('posts:follow_index'))
        index = response_index.context['page_obj']
        group = response_group.context['page_obj']
        profile = response_profile.context['page_obj']
        follower = response_follower.context['page_obj']
        for page in index:
            return page.text
        self.assertIn(post_new, index, 'Поста нет на главной')
        self.assertIn(post_new, group, 'Поста нет в профиле')
        self.assertIn(post_new, profile, 'Поста нет в группе')
        self.assertIn(post_new, follower, 'Поста нет на странице подписчика')

    def test_comment_added_correctly(self):
        """Комментарий к посту добавляется корректно"""
        comment_new = Comment.objects.create(text='Текст',
                                             author=self.user,
                                             post=self.post)
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertIn(comment_new, response)


class FollowViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Author')
        cls.follower = User.objects.create_user(username='Follower')
        cls.post = Post.objects.create(
            text='Текст',
            author=cls.author
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.follower)

    def test_profile_follow(self):
        """Можно подписаться на других пользователей"""
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.follower})
        )
        follow = Follow.objects.last()
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(follow.author, self.author)
        self.assertEqual(follow.user, self.follower)

    def test_profile_unfollow(self):
        """Можно отписаться от другого пользователя"""
        follow = Follow.objects.create(
            user=self.follower,
            author=self.author
        )
        self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.follower})
        )
        count_unfollow = Follow.objects.count()
        unfollow = Follow.objects.filter(
            author=self.author, user=self.follower
        )
        self.assertEqual(count_unfollow, 0)
        self.assertNotEqual(follow, unfollow)


class PaginatorViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test_slug',
            description='Тестовое описание'
        )
        for i in range(15):
            cls.post = Post.objects.create(
                author=cls.user,
                text='Тестовый текст' + str(i),
                pub_date='Дата',
                group=cls.group
            )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_index(self):
        """Тест пагинатора на главной."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), NUM_OF_POSTS)

    def test_post_group_list(self):
        """Тест пагинатора на странице группы."""
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.user.username}))
        self.assertEqual(len(response.context['page_obj']), NUM_OF_POSTS)
