from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.core.cache import cache
from mixer.backend.django import mixer

from posts.models import Post, Group, User


class PostsViewTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = mixer.blend(User)
        cls.group = mixer.blend(Group)
        cls.post = mixer.blend(Post, author=cls.user, group=cls.group)

        cls.URL_INDEX = ('posts:index', 'posts/index.html', None)
        cls.URL_GROUP_POSTS = ('posts:group_posts', 'posts/group_list.html',
                               (cls.group.slug,))
        cls.URL_PROFILE = ('posts:profile', 'posts/profile.html',
                           (cls.user.username,))
        cls.URL_POST_DETAIL = ('posts:post_detail', 'posts/post_detail.html',
                               (cls.post.pk,))
        cls.URL_CREATE = ('posts:post_create', 'posts/create_post.html', None)
        cls.URL_POST_EDIT = ('posts:post_edit', 'posts/create_post.html',
                             (cls.post.pk,))

    def setUp(self) -> None:
        self.anon = Client()
        self.auth = Client()
        self.auth.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = (
            self.URL_INDEX, self.URL_GROUP_POSTS, self.URL_PROFILE,
            self.URL_POST_DETAIL, self.URL_CREATE, self.URL_POST_EDIT
        )
        for url in templates_page_names:
            with self.subTest(template=url[1]):
                response = self.auth.get(reverse(url[0], args=url[2]))
                self.assertTemplateUsed(response, url[1])

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.auth.get(reverse(self.URL_INDEX[0]))
        first_object = response.context['page_obj'][0]
        group_title = first_object.group.title
        post_text = first_object.text
        group_slug = first_object.group.slug
        image = first_object.image
        self.assertEqual(group_title, self.group.title)
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(group_slug, self.group.slug)
        self.assertEqual(image, self.post.image)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.auth.get(reverse(
            self.URL_GROUP_POSTS[0], args=self.URL_GROUP_POSTS[2]))
        first_object = response.context['page_obj'][0]
        post_group = first_object.group.title
        image = first_object.image
        self.assertEqual(post_group, self.group.title)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(image, self.post.image)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.auth.get(reverse(
            self.URL_PROFILE[0], args=self.URL_PROFILE[2]))
        first_object = response.context['page_obj'][0]
        post_group = first_object.author
        image = first_object.image
        self.assertEqual(post_group, self.post.author)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(image, self.post.image)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.auth.get(reverse(
            self.URL_POST_DETAIL[0], args=self.URL_POST_DETAIL[2]))
        first_object = response.context['post']
        image = first_object.image
        self.assertEqual(first_object.pk, self.post.pk)
        self.assertEqual(image, self.post.image)

    def test_create_post_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.auth.get(reverse(self.URL_CREATE[0]))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_index_cache(self):
        """Тестим кэш индекса - ненавидим тесты"""
        Post.objects.all().delete()
        cache.clear()
        mixer.blend(Post, author=self.user)
        response1 = self.auth.get(reverse(self.URL_INDEX[0]))
        Post.objects.all().delete()
        response2 = self.auth.get(reverse(self.URL_INDEX[0]))
        self.assertEqual(response1.content, response2.content)
        cache.clear()
        response3 = self.auth.get(reverse(self.URL_INDEX[0]))
        self.assertNotEqual(response1.content, response3.content)

    def test_pages_uses_correct_template(self):
        """404  отдает кастомный шаблон."""
        response = self.anon.get('/unexisting_page/')
        self.assertTemplateUsed(response, 'core/404.html')


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = mixer.blend(User)
        cls.group = mixer.blend(Group)
        objs = (Post(author=cls.user, group=cls.group,
                text='Тестовый пост %s' % i) for i in range(13))
        cls.posts = Post.objects.bulk_create(objs)

        cls.URL_INDEX = ('posts:index', 'posts/index.html', None)
        cls.URL_GROUP_POSTS = ('posts:group_posts', 'posts/group_list.html',
                               (cls.group.slug,))
        cls.URL_PROFILE = ('posts:profile', 'posts/profile.html',
                           (cls.user.username,))

    def setUp(self):
        self.anon = Client()
        self.auth = Client()
        self.auth.force_login(self.user)

    def test_first_page_contains_ten_records(self):
        response = self.client.get(reverse(self.URL_INDEX[0]))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        response = self.client.get(reverse(self.URL_INDEX[0]) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_page_group_list_contains_ten_records(self):
        response = self.client.get(reverse(
            self.URL_GROUP_POSTS[0], args=self.URL_GROUP_POSTS[2]))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_first_page_profile_contains_ten_records(self):
        response = self.auth.get(reverse(
            self.URL_PROFILE[0], args=self.URL_PROFILE[2]))
        self.assertEqual(len(response.context['page_obj']), 10)
