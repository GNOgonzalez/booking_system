"""Studio blog posts — announcements visible on the home page."""

from scheduling.models import BlogPost
from scheduling.services.teacher_permissions import teacher_can, user_is_staff


def can_manage_blog(user):
    return teacher_can(user, 'manage_blog')


def list_published_posts():
    return BlogPost.objects.filter(is_published=True).select_related('author')


def list_manageable_posts(user):
    qs = BlogPost.objects.select_related('author')
    if user_is_staff(user):
        return qs
    return qs.filter(author=user)


def user_can_edit_post(user, post):
    if user_is_staff(user):
        return True
    return post.author_id == user.id and can_manage_blog(user)


def create_blog_post(user, *, title, body, image=None, is_published=True):
    if not can_manage_blog(user):
        return None, 'You do not have permission to publish blog posts.'
    from scheduling.services.uploads import validate_blog_image

    error = validate_blog_image(image)
    if error:
        return None, error
    post = BlogPost.objects.create(
        author=user,
        title=title.strip(),
        body=body.strip(),
        is_published=is_published,
    )
    if image:
        post.image = image
        post.save(update_fields=['image'])
    return post, None


def update_blog_post(post, user, **fields):
    if not user_can_edit_post(user, post):
        return None, 'Blog post not found.'

    image = fields.pop('image', None)
    clear_image = fields.pop('clear_image', False)
    from scheduling.services.uploads import validate_blog_image

    if image is not None:
        error = validate_blog_image(image)
        if error:
            return None, error

    for key in ('title', 'body', 'is_published'):
        if key in fields and fields[key] is not None:
            value = fields[key]
            if key in ('title', 'body'):
                value = value.strip()
            setattr(post, key, value)

    if clear_image and post.image:
        post.image.delete(save=False)
        post.image = ''
    elif image is not None:
        if post.image:
            post.image.delete(save=False)
        post.image = image

    post.save()
    return post, None


def delete_blog_post(post, user):
    if not user_can_edit_post(user, post):
        return False, 'Blog post not found.'
    if post.image:
        post.image.delete(save=False)
    post.delete()
    return True, None
