from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tweet', '0003_tweet_embedding'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tweet',
            name='embedding',
        ),
    ]
