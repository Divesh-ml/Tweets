from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import BooleanField, Count, Exists, OuterRef, Prefetch, Q, Value
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from .models import Follow, Tweet, TweetLike
from .forms import ReplyForm, TweetForm, UserRegistrationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login

# Create your views here.

def index(request):
    return render(request,'index.html')


def _replies_for_user(user):
    replies = Tweet.objects.select_related('user').annotate(
        like_count=Count('likes', distinct=True),
    )
    if user.is_authenticated:
        return replies.annotate(
            liked_by_user=Exists(
                TweetLike.objects.filter(tweet=OuterRef('pk'), user=user)
            ),
        )
    return replies.annotate(
        liked_by_user=Value(False, output_field=BooleanField()),
    )


def tweet_list(request):
    query = request.GET.get('q', '').strip()
    tweets = Tweet.objects.filter(reply_to__isnull=True).select_related(
        'user',
        'reply_to__user',
    ).annotate(
        reply_count=Count('replies', distinct=True),
    ).prefetch_related(
        Prefetch('replies', queryset=_replies_for_user(request.user), to_attr='prefetched_replies'),
    ).order_by('-created_at')
    if query:
        tweets = tweets.filter(
            Q(text__icontains=query) | Q(user__username__icontains=query)
        )
    return render(
        request,
        'tweet_list.html',
        {
            'tweets': tweets,
            'query': query,
        },
    )


@login_required
def following_tweets(request):
    query = request.GET.get('q', '').strip()
    followed_user_ids = request.user.following.values_list('followed_id', flat=True)
    tweets = Tweet.objects.filter(
        user_id__in=followed_user_ids,
        reply_to__isnull=True,
    ).select_related(
        'user',
        'reply_to__user',
    ).annotate(
        reply_count=Count('replies', distinct=True),
    ).prefetch_related(
        Prefetch('replies', queryset=_replies_for_user(request.user), to_attr='prefetched_replies'),
    ).order_by('-created_at')
    if query:
        tweets = tweets.filter(
            Q(text__icontains=query) | Q(user__username__icontains=query)
        )
    return render(
        request,
        'tweet_list.html',
        {
            'tweets': tweets,
            'query': query,
            'following_feed': True,
        },
    )


def people_list(request):
    query = request.GET.get('q', '').strip()
    users = User.objects.filter(is_active=True).annotate(
        follower_count=Count('followers', distinct=True),
    )
    if request.user.is_authenticated:
        users = users.exclude(pk=request.user.pk).annotate(
            is_following=Exists(
                Follow.objects.filter(follower=request.user, followed=OuterRef('pk'))
            )
        )
    else:
        users = users.annotate(is_following=Value(False, output_field=BooleanField()))
    if query:
        users = users.filter(username__icontains=query)
    return render(
        request,
        'people_list.html',
        {'people': users.order_by('username'), 'query': query},
    )


def user_profile(request, user_id):
    profile_user = get_object_or_404(User, pk=user_id, is_active=True)
    is_following = (
        request.user.is_authenticated
        and Follow.objects.filter(follower=request.user, followed=profile_user).exists()
    )
    tweets = Tweet.objects.filter(
        user=profile_user,
        reply_to__isnull=True,
    ).select_related(
        'reply_to__user',
    ).annotate(
        reply_count=Count('replies', distinct=True),
    ).prefetch_related(
        Prefetch('replies', queryset=_replies_for_user(request.user), to_attr='prefetched_replies'),
    ).order_by('-created_at')
    return render(
        request,
        'user_profile.html',
        {
            'profile_user': profile_user,
            'tweets': tweets,
            'is_following': is_following,
        },
    )


@login_required
@require_POST
def follow_user(request, user_id):
    followed = get_object_or_404(User, pk=user_id, is_active=True)
    if followed == request.user:
        messages.error(request, "You can't follow your own account.")
    else:
        Follow.objects.get_or_create(follower=request.user, followed=followed)
    return redirect('user_profile', user_id=followed.pk)


@login_required
@require_POST
def unfollow_user(request, user_id):
    followed = get_object_or_404(User, pk=user_id, is_active=True)
    Follow.objects.filter(follower=request.user, followed=followed).delete()
    return redirect('user_profile', user_id=followed.pk)


@login_required
@require_POST
def tweet_reply(request, tweet_id):
    parent_tweet = get_object_or_404(Tweet, pk=tweet_id)
    form = ReplyForm(request.POST)
    if form.is_valid():
        Tweet.objects.create(
            user=request.user,
            reply_to=parent_tweet,
            text=form.cleaned_data['text'],
        )
        messages.success(request, 'Your reply was posted.')
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        parts = urlsplit(next_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query['tweet'] = str(parent_tweet.pk)
        next_url = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )
        return redirect(next_url)
    return redirect(f"{reverse('tweet_list')}?tweet={parent_tweet.pk}")


@login_required
@require_POST
def toggle_tweet_like(request, tweet_id):
    reply = get_object_or_404(Tweet, pk=tweet_id, reply_to__isnull=False)
    action = request.POST.get('action')
    if action == 'like':
        TweetLike.objects.get_or_create(user=request.user, tweet=reply)
    elif action == 'unlike':
        TweetLike.objects.filter(user=request.user, tweet=reply).delete()
    else:
        messages.error(request, 'Invalid like action.')

    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        parts = urlsplit(next_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query['tweet'] = str(reply.reply_to_id)
        return redirect(
            urlunsplit(
                (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
            )
        )
    return redirect(f"{reverse('tweet_list')}?tweet={reply.reply_to_id}")


@login_required
def tweet_create(request):
    if request.method == 'POST':
        form = TweetForm(request.POST, request.FILES)
        if form.is_valid():
            tweet = form.save(commit=False)
            tweet.user = request.user
            tweet.save()
            return redirect('tweet_list')
    else:
        form = TweetForm()
    return render(request, 'tweet_form.html',{'form':form})

@login_required
def tweet_edit(request,tweet_id):
    tweet = get_object_or_404(Tweet, pk=tweet_id, user=request.user)
    if request.method == 'POST':
        form = TweetForm(request.POST, request.FILES, instance=tweet)
        if form.is_valid():
            tweet= form.save(commit=False)
            tweet.user = request.user
            tweet.save()
            return redirect('tweet_list')

    else:
        form = TweetForm(instance=tweet)
    return render(request, 'tweet_form.html',{'form':form})

@login_required
def tweet_delete(request, tweet_id):
    tweet = get_object_or_404(Tweet, pk=tweet_id, user= request.user)
    if request.method == 'POST':
        tweet.delete()
        return redirect('tweet_list')
    return render(request, 'tweet_confirm_delete.html',{'tweet':tweet})

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            login(request, user)
            return redirect('tweet_list')
        
    else:
        form = UserRegistrationForm()
        
        
    return render(request, 'registration/register.html',{'form':form})

    