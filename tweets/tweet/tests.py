from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from .models import Follow, Tweet, TweetLike


class TweetFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            password='TweetPassword123!',
        )

    def test_login_and_register_pages_render(self):
        login_response = self.client.get(reverse('login'))
        register_response = self.client.get(reverse('register'))

        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, '<label class="form-label" for="id_username">Username</label>', html=True)
        self.assertContains(login_response, '<label class="form-label" for="id_password">Password</label>', html=True)
        self.assertContains(login_response, 'Enter your username and password to log in.')
        self.assertEqual(register_response.status_code, 200)
        for label in ('Username', 'Email address', 'Password', 'Confirm password'):
            self.assertContains(register_response, label)

    def test_login_authenticates_existing_user(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'alice', 'password': 'TweetPassword123!'},
        )

        self.assertRedirects(response, '/tweet/')
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_registration_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password1': 'StrongPassword123!',
                'password2': 'StrongPassword123!',
            },
        )

        self.assertRedirects(response, reverse('tweet_list'))
        self.assertTrue(
            User.objects.get(username='newuser').check_password('StrongPassword123!')
        )
        self.assertEqual(int(self.client.session['_auth_user_id']), User.objects.get(username='newuser').pk)

    def test_search_matches_tweet_text_and_username(self):
        Tweet.objects.create(user=self.user, text='A sunny day')
        another_user = User.objects.create_user(username='bob', password='TweetPassword123!')
        Tweet.objects.create(user=another_user, text='A quiet update')

        text_results = self.client.get(reverse('tweet_list'), {'q': 'sunny'})
        user_results = self.client.get(reverse('tweet_list'), {'q': 'bob'})
        legacy_mode_results = self.client.get(
            reverse('tweet_list'),
            {'q': 'sunny', 'mode': 'semantic'},
        )

        self.assertContains(text_results, 'A sunny day')
        self.assertNotContains(text_results, 'A quiet update')
        self.assertContains(user_results, 'A quiet update')
        self.assertContains(legacy_mode_results, 'A sunny day')
        self.assertNotContains(legacy_mode_results, 'Meaning')

    def test_tweet_detail_modal_lists_replies_and_zoomable_image(self):
        parent = Tweet.objects.create(user=self.user, text='Look at this photo')
        reply = Tweet.objects.create(user=self.user, reply_to=parent, text='Nice picture')

        response = self.client.get(reverse('tweet_list'))

        self.assertContains(response, 'tweetDetailModal')
        self.assertContains(response, 'data-tweet-id="{}"'.format(parent.pk))
        self.assertNotContains(response, 'data-tweet-id="{}"'.format(reply.pk))
        self.assertContains(response, 'Nice picture')
        self.assertContains(response, 'is-zoomed')
        self.assertContains(response, 'Open / Reply')

    def test_replies_do_not_appear_as_separate_feed_or_profile_cards(self):
        parent = Tweet.objects.create(user=self.user, text='Original post')
        bob = User.objects.create_user(username='bob', password='TweetPassword123!')
        reply = Tweet.objects.create(user=bob, reply_to=parent, text='A separate reply')
        Follow.objects.create(follower=self.user, followed=bob)
        self.client.force_login(self.user)

        feed_response = self.client.get(reverse('tweet_list'))
        following_response = self.client.get(reverse('following_tweets'))
        profile_response = self.client.get(reverse('user_profile', args=[bob.pk]))

        self.assertContains(feed_response, 'Original post')
        self.assertNotContains(feed_response, 'data-tweet-id="{}"'.format(reply.pk))
        self.assertNotContains(following_response, 'data-tweet-id="{}"'.format(reply.pk))
        self.assertNotContains(profile_response, 'data-tweet-id="{}"'.format(reply.pk))

    def test_authenticated_user_can_reply_and_return_to_open_tweet(self):
        parent = Tweet.objects.create(user=self.user, text='Interview tip')
        bob = User.objects.create_user(username='bob', password='TweetPassword123!')
        self.client.force_login(bob)

        response = self.client.post(
            reverse('tweet_reply', args=[parent.pk]),
            {'text': 'Thanks for sharing', 'next': reverse('tweet_list')},
        )

        self.assertRedirects(
            response,
            f'{reverse("tweet_list")}?tweet={parent.pk}',
        )
        reply = Tweet.objects.get(reply_to=parent)
        self.assertEqual(reply.user, bob)
        self.assertEqual(reply.text, 'Thanks for sharing')

    def test_reply_requires_login_and_rejects_empty_text(self):
        parent = Tweet.objects.create(user=self.user, text='Original tweet')
        guest_response = self.client.post(
            reverse('tweet_reply', args=[parent.pk]),
            {'text': 'A reply'},
        )
        self.assertRedirects(
            guest_response,
            f"{reverse('login')}?next={reverse('tweet_reply', args=[parent.pk])}",
        )

        self.client.force_login(self.user)
        invalid_response = self.client.post(
            reverse('tweet_reply', args=[parent.pk]),
            {'text': '   '},
        )
        self.assertRedirects(
            invalid_response,
            f'{reverse("tweet_list")}?tweet={parent.pk}',
        )
        self.assertFalse(Tweet.objects.filter(reply_to=parent).exists())

    def test_user_can_like_and_unlike_a_reply_once(self):
        parent = Tweet.objects.create(user=self.user, text='Original tweet')
        reply = Tweet.objects.create(user=self.user, reply_to=parent, text='Helpful comment')
        bob = User.objects.create_user(username='bob', password='TweetPassword123!')
        self.client.force_login(bob)
        like_url = reverse('toggle_tweet_like', args=[reply.pk])
        return_to_modal = f'{reverse("tweet_list")}?tweet={parent.pk}'

        response = self.client.post(
            like_url,
            {'action': 'like', 'next': reverse('tweet_list')},
        )
        self.assertRedirects(response, return_to_modal)
        self.client.post(like_url, {'action': 'like', 'next': reverse('tweet_list')})
        self.assertEqual(TweetLike.objects.filter(user=bob, tweet=reply).count(), 1)

        modal_response = self.client.get(reverse('tweet_list'))
        self.assertContains(modal_response, 'Unlike')
        self.assertContains(modal_response, '1 like')

        self.client.post(like_url, {'action': 'unlike', 'next': reverse('tweet_list')})
        self.assertFalse(TweetLike.objects.filter(user=bob, tweet=reply).exists())

    def test_reply_like_requires_login_and_only_accepts_replies(self):
        parent = Tweet.objects.create(user=self.user, text='Original tweet')
        reply = Tweet.objects.create(user=self.user, reply_to=parent, text='A reply')
        guest_response = self.client.post(
            reverse('toggle_tweet_like', args=[reply.pk]),
            {'action': 'like'},
        )
        self.assertRedirects(
            guest_response,
            f"{reverse('login')}?next={reverse('toggle_tweet_like', args=[reply.pk])}",
        )

        self.client.force_login(self.user)
        non_reply_response = self.client.post(
            reverse('toggle_tweet_like', args=[parent.pk]),
            {'action': 'like'},
        )
        self.assertEqual(non_reply_response.status_code, 404)

    def test_guest_create_button_redirects_to_login(self):
        response = self.client.get(reverse('tweet_create'))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('tweet_create')}")

    def test_create_tweet_uploads_and_displays_photo(self):
        image_data = BytesIO()
        Image.new('RGB', (1, 1), color='red').save(image_data, format='PNG')
        image = SimpleUploadedFile(
            'tweet.png',
            image_data.getvalue(),
            content_type='image/png',
        )
        self.client.force_login(self.user)

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse('tweet_create'),
                {'text': 'Photo tweet', 'photo': image},
            )

            self.assertRedirects(response, reverse('tweet_list'))
            tweet = Tweet.objects.get(text='Photo tweet')
            self.assertTrue(tweet.photo.name.startswith('photos/'))
            self.assertContains(self.client.get(reverse('tweet_list')), tweet.photo.url)

            with override_settings(DEBUG=False, MEDIA_ROOT=media_root):
                photo_response = self.client.get(tweet.photo.url)

            try:
                self.assertEqual(photo_response.status_code, 200)
                self.assertEqual(photo_response['Content-Type'], 'image/png')
            finally:
                photo_response.close()

    def test_follow_and_unfollow_another_user(self):
        bob = User.objects.create_user(username='bob', password='TweetPassword123!')
        self.client.force_login(self.user)

        follow_response = self.client.post(reverse('follow_user', args=[bob.pk]))
        self.assertRedirects(follow_response, reverse('user_profile', args=[bob.pk]))
        self.assertTrue(Follow.objects.filter(follower=self.user, followed=bob).exists())

        unfollow_response = self.client.post(reverse('unfollow_user', args=[bob.pk]))
        self.assertRedirects(unfollow_response, reverse('user_profile', args=[bob.pk]))
        self.assertFalse(Follow.objects.filter(follower=self.user, followed=bob).exists())

    def test_follow_action_requires_login_and_post(self):
        bob = User.objects.create_user(username='bob', password='TweetPassword123!')
        response = self.client.post(reverse('follow_user', args=[bob.pk]))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('follow_user', args=[bob.pk])}",
        )

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('follow_user', args=[bob.pk])).status_code, 405)
        self.assertFalse(Follow.objects.exists())

    def test_user_cannot_follow_themselves_and_following_feed_is_scoped(self):
        bob = User.objects.create_user(username='bob', password='TweetPassword123!')
        Follow.objects.create(follower=self.user, followed=bob)
        Tweet.objects.create(user=self.user, text='My own post')
        Tweet.objects.create(user=bob, text='Followed post')
        self.client.force_login(self.user)

        self.client.post(reverse('follow_user', args=[self.user.pk]))
        response = self.client.get(reverse('following_tweets'))

        self.assertEqual(Follow.objects.count(), 1)
        self.assertContains(response, 'Followed post')
        self.assertNotContains(response, 'My own post')

    def test_people_search_and_profile_show_follow_data(self):
        bob = User.objects.create_user(username='bob', password='TweetPassword123!')
        Follow.objects.create(follower=self.user, followed=bob)
        self.client.force_login(self.user)

        people_response = self.client.get(reverse('people_list'), {'q': 'bob'})
        profile_response = self.client.get(reverse('user_profile', args=[bob.pk]))

        self.assertContains(people_response, 'bob')
        self.assertNotContains(people_response, 'alice')
        self.assertContains(profile_response, '1 follower')
        self.assertContains(profile_response, 'Unfollow')
