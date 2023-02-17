from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.user_for_test_edit = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='test_group',
            slug='test_slug',
            description='test_description',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cache.clear()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client_for_edit = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_for_edit.force_login(self.user_for_test_edit)
        cache.clear()

    def test_urls_templates(self):
        """Проверяет, что url использует требуемые шаблоны"""
        template_url_name = (
            ['/', 'posts/index.html'],
            [f'/group/{self.group.slug}/', 'posts/group_list.html'],
            [f'/profile/{self.user.username}/', 'posts/profile.html'],
            [f'/posts/{self.post.id}/', 'posts/post_detail.html'],
            ['/create/', 'posts/create_post.html'],
        )
        for value in template_url_name:
            with self.subTest(value=value[0]):
                response = self.authorized_client.get(value[0])
                self.assertTemplateUsed(response, value[1])

    def test_404_url(self):
        """Проверяет, что при запросе к
         несуществующему url, будет ошибка 404"""
        response_url = {
            self.guest_client: '/page-not-found/',
            self.authorized_client: '/and-not-found-too/',
        }
        for client, url in response_url.items():
            with self.subTest(client=client):
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_exists_at_desired_lokation(self):
        """Проверяет, что index, group_list, profile и post_detail
         доступны неавторизованному клиенту"""
        urls_http_status = (
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user.username}/',
            f'/posts/{self.post.pk}/',
        )
        for value in urls_http_status:
            with self.subTest(value=value):
                response = self.guest_client.get(value)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_access_right(self):
        """Проверяет, что страница редактирования
         поста доступна только автору"""
        response = self.guest_client.get(f'/posts/{self.post.pk}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.authorized_client.get(f'/posts/{self.post.pk}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.authorized_client_for_edit.get(
            f'/posts/{PostURLTests.post.pk}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_create_post_access_right(self):
        """Проверяет, что страница создания поста
         доступна только авторизованному пользователю"""
        response = self.guest_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
