from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
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
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def url_exists_at_desired_location(self):
        """Страницы доступны пользователям"""
        any_user_status_codes = {
            '/': HTTPStatus.OK.value,
            '/group/test_slug/': HTTPStatus.OK.value,
            '/profile/NoName/': HTTPStatus.OK.value,
            f'/posts/{self.post.id}/': HTTPStatus.OK.value
        }
        authorized_user_status_code = {
            '/create/': HTTPStatus.OK.value,
            f'/posts/{self.post.id}/comment/': HTTPStatus.OK.value,
            '/follow/': HTTPStatus.OK.value,
            '/profile/NoName/follow/': HTTPStatus.OK.value,
            '/profile/NoName/unfollow': HTTPStatus.OK.value
        }
        author_status_code = {
            f'/posts/{self.post.id}/edit/': HTTPStatus.OK.value
        }
        for address, status in any_user_status_codes.items():
            with self.subTest(status=status):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, status)
        for address, status in authorized_user_status_code.items():
            with self.subTest(status=status):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, status)
        for address, status in author_status_code.items():
            with self.subTest(status=status):
                if self.user == self.post.author:
                    response = self.authorized_client.get(address)
                    self.assertEqual(response.status_code, status)

    def test_unexisted_url_redirect_anonymous(self):
        """Страница /unexisting_page/ вернёт ошибку 404"""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND.value)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон"""
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': '/group/test_slug/',
            'posts/profile.html': '/profile/NoName/',
            'posts/post_detail.html': f'/posts/{self.post.id}/',
            'posts/create_post.html': '/create/',
            'posts/follow.html': '/follow/'
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
