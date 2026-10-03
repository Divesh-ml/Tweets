from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Tweet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='replies',
        blank=True,
        null=True,
    )
    text = models.TextField(max_length=240)
    photo = models.ImageField(upload_to='photos/',blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.user.username} - {self.text[:10]}'


class Follow(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
    )
    followed = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'followed'],
                name='unique_user_follow',
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F('followed')),
                name='prevent_self_follow',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.follower.username} follows {self.followed.username}'


class TweetLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tweet_likes')
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'tweet'],
                name='unique_user_tweet_like',
            ),
        ]

    def __str__(self):
        return f'{self.user.username} likes tweet #{self.tweet_id}'