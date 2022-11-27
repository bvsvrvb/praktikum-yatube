from django.test import TestCase, Client
from mixer.backend.django import mixer
from http import HTTPStatus
from django.urls import reverse
from django.core.cache import cache

from posts.models import Post, Group, User, Comment


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = mixer.blend(User)
        cls.group = mixer.blend(Group)
        cls.post = mixer.blend(Post, author=cls.user, group=cls.group)
        cls.comments = mixer.blend(Comment, author=cls.user, post=cls.post)

        cls.URL_INDEX = ('posts:index', 'posts/index.html', None, None)
        cls.URL_GROUP_POSTS = ('posts:group_posts', 'posts/group_list.html',
                               (cls.group.slug,), None)
        cls.URL_PROFILE = ('posts:profile', 'posts/profile.html',
                           (cls.user.username,), None)
        cls.URL_POST_DETAIL = ('posts:post_detail', 'posts/post_detail.html',
                               (cls.post.pk,), None)
        cls.URL_CREATE = ('posts:post_create', 'posts/create_post.html', None,
                          '/auth/login/?next=/create/')
        cls.URL_POST_EDIT = ('posts:post_edit', 'posts/create_post.html',
                             (cls.post.pk,), '/auth/login/?next='
                             f'/posts/{cls.post.pk}/edit/')
        cls.URL_POST_COMMENT = ('posts:add_comment', 'posts/post_detail.html',
                                (cls.post.pk,), '/auth/login/?next='
                                f'/posts/{cls.post.pk}/comment/')

    def setUp(self) -> None:
        self.anon = Client()
        self.auth = Client()
        self.auth.force_login(self.user)

    def test_urls_templates(self):
        """URL-адрес использует соответствующий шаблон."""
        urls_templates = (
            self.URL_INDEX, self.URL_GROUP_POSTS, self.URL_PROFILE,
            self.URL_POST_DETAIL, self.URL_CREATE, self.URL_POST_EDIT
        )
        for url in urls_templates:
            with self.subTest(template=url[1]):
                cache.clear()
                response = self.auth.get(reverse(url[0], args=url[2]))
                self.assertTemplateUsed(response, url[1])

    def test_unexisting_url(self):
        """Несуществующий URL выдает 404."""
        response = self.anon.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_url_exists_common(self):
        """URL-адреса доступны любому пользователю."""
        urls_responses = (
            self.URL_INDEX, self.URL_GROUP_POSTS, self.URL_PROFILE,
            self.URL_POST_DETAIL,
        )
        for url in urls_responses:
            with self.subTest(url=url[0]):
                response = self.anon.get(reverse(url[0], args=url[2]))
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_exists_auth(self):
        """URL-адреса доступны авторизованному пользователю."""
        urls_responses = (self.URL_CREATE, self.URL_POST_EDIT)
        for url in urls_responses:
            with self.subTest(url=url[0]):
                response = self.auth.get(reverse(url[0], args=url[2]))
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_redirect_anonymous(self):
        """URL-адреса корректно перенаправляют анонимных пользователей"""
        urls_redirects = (
            self.URL_CREATE,
            self.URL_POST_EDIT,
            self.URL_POST_COMMENT
        )
        for url in urls_redirects:
            with self.subTest(url=url[0]):
                response = self.anon.get(reverse(url[0], args=url[2]))
                self.assertRedirects(response, url[3])

    def test_url_redirect_non_author(self):
        """Страница /posts/{PostsURLTests.post.pk}/edit/ перенаправит
        не автора поста на страницу информации о посте"""
        self.non_author = User.objects.create_user(username='fakeman')
        self.auth.force_login(self.non_author)
        response = self.auth.get(reverse(
            self.URL_POST_EDIT[0], args=self.URL_POST_EDIT[2]))
        self.assertRedirects(response, reverse(
            self.URL_POST_DETAIL[0], args=self.URL_POST_DETAIL[2]))

    def test_url_comment_auth(self):
        """Комментирование доступно авторизованному пользователю"""
        response = self.auth.get(reverse(
            self.URL_POST_COMMENT[0], args=self.URL_POST_COMMENT[2]))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
