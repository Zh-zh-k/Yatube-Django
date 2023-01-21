from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post
from ..utils import NUM_OF_POSTS

User = get_user_model()


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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            pub_date='Дата'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

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
        """Проверка контекста поста."""
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author, self.user)
        self.assertEqual(first_object.group, self.group)

    def text_index_page_show_correct_context(self):
        """Главная страница показывает нужный контекст."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)

    def test_group_page_show_correct_context(self):
        """Страница группы показывает нужный контекст."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group.slug})
        )
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)
        self.assertEqual(response.context['group'], self.group)

    def test_profile_page_show_correct_context(self):
        """Страница профиля показывает нужный контекст."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'NoName'})
        )
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)
        self.assertEqual(response.context['author'], self.user)

    def test_post_detail_page_show_correct_context(self):
        """Страница поста показывает нужный контекст."""
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context['post'].text, self.post.text,
                         'Не совпадает текст')
        self.assertEqual(response.context['post'].group, self.group,
                         'Не совпадает группа')
        self.assertEqual(response.context['post'].pub_date, self.post.pub_date,
                         'Не совпадает дата публикации')
        self.assertEqual(response.context['post'].author, self.user,
                         'Не совпадает автор')

    def test_create_post_form_show_correct_context(self):
        """Страница создания поста показывает нужный контекст."""
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
        """Страница редактирования поста показывает нужный контекст."""
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
        """Пост добавляется корректно."""
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
        index = response_index.context['page_obj']
        group = response_group.context['page_obj']
        profile = response_profile.context['page_obj']
        for page in index:
            return page.text
        self.assertIn(post_new, index, 'Поста нет на главной')
        self.assertIn(post_new, group, 'Поста нет в профиле')
        self.assertIn(post_new, profile, 'Поста нет в группе')


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
