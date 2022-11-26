import tempfile
import shutil

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from mixer.backend.django import mixer

from posts.models import Post, Group, User, Comment


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mixer.blend(User)
        cls.group = mixer.blend(Group)
        cls.post = mixer.blend(Post, author=cls.user, group=cls.group)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.anon = Client()
        self.auth = Client()
        self.auth.force_login(self.user)

    def test_create_comment(self):
        """Валидная форма создает запись в Comment."""
        comments_count = Comment.objects.count()
        self.auth.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data={'text': 'Тестовый комментарий'},
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        comment1 = Comment.objects.first()
        self.assertEqual(
            comment1.text, 'Тестовый комментарий'
        )
        self.assertEqual(
            comment1.author, self.user
        )
        self.assertEqual(
            comment1.post, self.post
        )

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        Post.objects.all().delete()
        posts_count = Post.objects.count()
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
            content_type='image/gif'
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.auth.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', args=(self.user.username,)))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post1 = Post.objects.first()
        self.assertEqual(
            post1.text, form_data['text']
        )
        self.assertEqual(
            post1.group.id, form_data['group']
        )
        self.assertEqual(
            post1.image.file.name,
            TEMP_MEDIA_ROOT + '/posts/' + form_data['image'].name
        )

    def test_edit_post(self):
        """Валидная форма редактирует пост."""
        posts_count = Post.objects.count()
        response = self.auth.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data={'text': 'ГосподеИИсусе, да сколько же этих тестов,'
                  'когда они уже закончатся :( AAAAAAAAAAAAAA',
                  },
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=(self.post.pk,)))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                text='ГосподеИИсусе, да сколько же этих тестов,'
                     'когда они уже закончатся :( AAAAAAAAAAAAAA',
            ).exists()
        )
