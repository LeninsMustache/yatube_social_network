from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import SYMB_IN_TEXT, Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост длиной более 15 символов',
        )

    def test_text_models_have_correct_object_names(self):
        """Проверяет, правильно ли отображается значение
         поля __str__ в объектах модели Post."""
        post = PostModelTest.post
        text = post.text[:SYMB_IN_TEXT]
        self.assertEqual(text, str(post))

    def test_group_models_have_correct_object_names(self):
        """Проверяет, правильно ли отображается значение
         поля __str__ в объектах модели Group."""
        group = PostModelTest.group
        group_title = group.title
        self.assertEqual(group_title, str(group))
