import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста',
            group=cls.group,
        )
        cls.form = PostForm()
        cls.form_data_comment = {
            'author': cls.user,
            'post': cls.post,
            'text': 'Тестовый комментарий',
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        """Чистим папку с медиа, чтобы прошел тест изменения поста с картинкой,
        т.к. перед этим создается картинка с таким же именем"""
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        self.form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
            'image': self.uploaded
        }

    def test_form_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=self.form_data['text'],
                group=self.form_data['group'],
                image='posts/small.gif',
                author=self.post.author
            ).exists()
        )

    def test_post_edit(self):
        """Проверяет, что отредактированный пост
        сохраняется в БД и перенаправляет пользователя
         на страницу измененного поста"""
        post_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=self.form_data,
            follow=True)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={
                'post_id': self.post.pk
            }))
        self.assertEqual(Post.objects.count(), post_count)
        self.assertTrue(
            Post.objects.filter(
                text=self.form_data['text'],
                group=self.form_data['group'],
                image='posts/small.gif',
                author=self.post.author
            ).exists()
        )

    def test_add_comment(self):
        """Комментарии не может оставлять неавторизованный пользователь"""
        comments_count = Comment.objects.count()
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={
                'post_id': self.post.id
            }),
            data=self.form_data_comment,
            follow=True
        )

        self.assertEqual(comments_count, Comment.objects.count())
        self.assertFalse(Comment.objects.filter(
            text=self.form_data_comment['text'],
            author=self.form_data_comment['author'],
            post=self.form_data_comment['post']
        ))

    def test_add_comment_authorized(self):
        """Авторизованный пользователь может оставить комментарий"""
        comments_count = Comment.objects.count()
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={
                'post_id': self.post.id
            }),
            data=self.form_data_comment,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(
            text=self.form_data_comment['text'],
            author=self.form_data_comment['author'],
            post=self.form_data_comment['post']
        ))
