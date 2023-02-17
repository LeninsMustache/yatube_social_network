import shutil
import tempfile
from random import randint

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post
from ..utils import POSTS_ON_ONE_PAGE

SECOND_PAGE_POSTS = randint(1, POSTS_ON_ONE_PAGE)
TOTAL_POSTS = POSTS_ON_ONE_PAGE + SECOND_PAGE_POSTS


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.second_user = User.objects.create_user(username='Mikhail')
        cls.third_user = User.objects.create_user(username='author2')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.post = Post.objects.bulk_create(
            Post(
                author=cls.user,
                text=f'Тестовый пост{i}',
                group=cls.group, id=f'{i}'
            ) for i in range(TOTAL_POSTS))
        cls.form_fields = (
            ['text', forms.fields.CharField],
            ['group', forms.models.ModelChoiceField],
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.form_data = {
            'text': 'Тестовый текст',
            'group': cls.group.pk,
            'image': cls.uploaded
        }
        cls.form_data_comment = {
            'author': cls.user,
            'post': Post.objects.latest('created'),
            'text': 'Тестовый комментарий',
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        cache.clear()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.another_authorized_client = Client()
        self.third_autorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.another_authorized_client.force_login(self.second_user)
        self.third_autorized_client.force_login(self.third_user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """Проверяет, что страница использует требуемые шаблоны"""
        templates_pages_names = (
            [reverse('posts:post_create'), 'posts/create_post.html'],
            [reverse('posts:index'), 'posts/index.html'],
            [reverse('posts:group_list', kwargs={
                'slug': self.group.slug
            }), 'posts/group_list.html'],
            [reverse('posts:profile', kwargs={
                'username': ViewsPagesTests.post[0].author.username
            }), 'posts/profile.html'],
            [reverse('posts:post_detail', kwargs={
                'post_id': self.post[0].pk
            }), 'posts/post_detail.html'],
            [reverse('posts:post_edit', kwargs={
                'post_id': self.post[0].pk
            }), 'posts/create_post.html'],
        )
        for template in templates_pages_names:
            with self.subTest(template=template[0]):
                response = self.authorized_client.get(template[0])
                self.assertTemplateUsed(response, template[1])

    def test_index_show_correct_context(self):
        """Проверяет, что в шаблон главной
         страницы передан ожидаемый контекст"""
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        response = self.authorized_client.get(reverse('posts:index'))
        post_obj = response.context['page_obj'][0]
        post_latest = Post.objects.latest('created')
        self.assertEqual(post_obj, post_latest)

    def test_group_list_show_correct_context(self):
        """Проверяет, что в шаблон
         страницы группы передан ожидаемый контекст"""
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': ViewsPagesTests.group.slug}
            ))
        post_obj = response.context['page_obj'][0]
        post_latest = Post.objects.latest('created')
        self.assertEqual(post_obj, post_latest)
        self.assertEqual(post_obj.group, response.context.get('group'))

    def test_profile_show_correct_context(self):
        """Проверяет, что в шаблон профиля передан ожидаемый контекст"""
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        page_object = response.context['page_obj'][0]
        author = self.user
        latest_post_of_author = author.posts.latest('created')
        self.assertEqual(latest_post_of_author, page_object)
        self.assertEqual(
            latest_post_of_author.author, response.context.get('author'))

    def test_post_detail_show_correct_context(self):
        """Проверяет, что в шаблон поста передан ожидаемый контекст"""
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={
                'post_id': Post.objects.latest('created').id
            }))
        first_object = response.context['post']
        post = Post.objects.latest('created')
        self.assertEqual(first_object, post)
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={
                'post_id': Post.objects.latest('created').id
            }),
            data=self.form_data_comment,
            follow=True
        )
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={
                'post_id': Post.objects.latest('created').id
            }))
        comment = response.context['comments'][0]
        self.assertEqual(comment.author, self.form_data_comment['author'])
        self.assertEqual(comment.text, self.form_data_comment['text'])
        self.assertEqual(comment.post, Post.objects.latest('created'))

    def test_create_post_show_correct_context(self):
        """Проверяет, что поля формы
        создания поста соответствуют контексту"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        for value in self.form_fields:
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value[0])
                self.assertIsInstance(form_field, value[1])

    def test_edit_post_show_correct_context(self):
        """Проверяет, что поля формы
         редактирования поста соотвествуют контексту"""
        author = self.user
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={
                'post_id': author.posts.latest('created').id
            }))
        for value in self.form_fields:
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value[0])
                self.assertIsInstance(form_field, value[1])

    def test_first_page_contains_ten_records(self):
        """Проверка работы пэджинатора на
         первой странице index, group_list и profile"""
        first_page = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={
                'slug': self.group.slug
            }),
            reverse('posts:profile', kwargs={
                'username': self.user
            }),
        )
        for value in first_page:
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                self.assertEqual(
                    len(response.context['page_obj']), POSTS_ON_ONE_PAGE)

    def test_second_page_contains_another_records(self):
        """Проверка работы пэджинатора на
        второй странице index, group_list и profile"""
        second_page = (
            reverse('posts:index') + '?page=2',
            reverse('posts:group_list', kwargs={
                'slug': self.group.slug
            }) + '?page=2',
            reverse('posts:profile', kwargs={
                'username': self.user
            }) + '?page=2',
        )
        for value in second_page:
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                self.assertEqual(
                    len(response.context['page_obj']), SECOND_PAGE_POSTS)

    def test_created_post_is_shown(self):
        """Проверяет, что созданный пост отображается
         на главной странице, в профиле автора
         и на странице соответствующей группы"""
        new_post = Post.objects.create(
            author=self.second_user,
            text='--empty--',
            group=Group.objects.create(
                title='new_group',
                description='--empty--',
                slug='test-slug-3',
            )
        )
        reverse_names_new_post = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={
                'slug': new_post.group.slug}),
            reverse('posts:profile', kwargs={
                'username': new_post.author.username}),
        )
        for value in reverse_names_new_post:
            with self.subTest(value=value):
                self.assertContains(
                    self.authorized_client.get(value), new_post)

    def test_new_post_with_group_is_not_in_another_group_list(self):
        """Проверяет, что созданный пост
        не отображается на странице другой группы"""
        new_post = Post.objects.create(
            author=self.second_user,
            text='--empty--',
            group=Group.objects.create(
                title='new_group',
                description='--empty--',
                slug='test-slug-3',
            )
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={
                'slug': ViewsPagesTests.group.slug
            }))
        self.assertNotContains(response, new_post)

    def test_index_page_cach(self):
        post = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Тестируем кэширование'
        )
        reverse_addr = reverse('posts:index')
        content1 = self.client.get(reverse_addr).content
        post.delete()
        content2 = self.client.get(reverse_addr).content
        self.assertEqual(content1, content2)
        cache.clear()
        content3 = self.client.get(reverse_addr).content
        self.assertNotEqual(content1, content3)

    def test_unfollow(self):
        """Проверка работы отписки от автора"""
        follow = Follow.objects.create(
            user=self.user,
            author=self.second_user
        )
        follows_count = Follow.objects.count()
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': follow.author}
            )
        )
        self.assertNotEqual(Follow.objects.count(), follows_count)

    def test_follow(self):
        """Проверка работы подписки на автора"""
        follows_count = Follow.objects.count()
        self.another_authorized_client.get(
            reverse('posts:profile_follow', kwargs={
                'username': self.user.username
            })
        )
        self.assertEqual(Follow.objects.count(), follows_count + 1)

    def test_correct_subscribtion(self):
        """Проверка появления нового поста в ленте подписчика"""
        Follow.objects.create(user=self.user, author=self.second_user)
        Post.objects.create(
            author=self.second_user,
            group=self.group,
            text='Тест подписки'
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        post_obj = response.context['page_obj'][0]
        self.assertEqual(post_obj.author, self.second_user)
        self.assertEqual(post_obj.group, self.group)
        self.assertEqual(post_obj.text, 'Тест подписки')

    def test_correct_subscribtion_not_subscriber(self):
        Follow.objects.create(user=self.user, author=self.second_user)
        Follow.objects.create(user=self.third_user, author=self.user)
        Post.objects.create(
            author=self.second_user,
            group=self.group,
            text='Тест подписки'
        )
        response = self.third_autorized_client.get(reverse(
            'posts:follow_index'))
        post_obj = response.context['page_obj'][0]
        self.assertNotEqual(post_obj.author, self.second_user)
        self.assertNotEqual(post_obj.text, 'Тест подписки')
