"""Blog post API — home page announcements."""

from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.api.serializers import BlogPostSerializer
from scheduling.models import BlogPost
from scheduling.services.blog import (
    can_manage_blog,
    create_blog_post,
    delete_blog_post,
    list_manageable_posts,
    list_published_posts,
    update_blog_post,
    user_can_edit_post,
)
from scheduling.services.teacher_permissions import permission_denied_response
from scheduling.services.uploads import upload_limits_payload


class UploadLimitsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(upload_limits_payload())


class BlogPostListView(generics.ListAPIView):
    """Published posts for the home page feed."""

    permission_classes = [IsAuthenticated]
    serializer_class = BlogPostSerializer

    def get_queryset(self):
        return list_published_posts()


class BlogPostManageListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        if not can_manage_blog(request.user):
            return permission_denied_response('manage_blog')
        posts = list_manageable_posts(request.user)
        serializer = BlogPostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        if not can_manage_blog(request.user):
            return permission_denied_response('manage_blog')
        title = request.data.get('title', '').strip()
        body = request.data.get('body', '').strip()
        if not title or not body:
            return Response({'detail': 'Title and body are required.'}, status=status.HTTP_400_BAD_REQUEST)
        is_published = str(request.data.get('is_published', 'true')).lower() not in ('false', '0', 'no')
        post, error = create_blog_post(
            request.user,
            title=title,
            body=body,
            image=request.FILES.get('image'),
            is_published=is_published,
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            BlogPostSerializer(post, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class BlogPostDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, request, pk):
        post = BlogPost.objects.select_related('author').filter(pk=pk).first()
        if post is None:
            return None
        if post.is_published:
            return post
        if user_can_edit_post(request.user, post):
            return post
        return None

    def get(self, request, pk):
        post = self.get_object(request, pk)
        if post is None:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(BlogPostSerializer(post, context={'request': request}).data)

    def patch(self, request, pk):
        post = BlogPost.objects.select_related('author').filter(pk=pk).first()
        if post is None or not user_can_edit_post(request.user, post):
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        fields = {}
        if 'title' in request.data:
            fields['title'] = request.data.get('title')
        if 'body' in request.data:
            fields['body'] = request.data.get('body')
        if 'is_published' in request.data:
            fields['is_published'] = str(request.data.get('is_published')).lower() not in ('false', '0', 'no')
        if 'image' in request.FILES:
            fields['image'] = request.FILES.get('image')
        if str(request.data.get('clear_image', '')).lower() in ('true', '1', 'yes'):
            fields['clear_image'] = True

        updated, error = update_blog_post(post, request.user, **fields)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BlogPostSerializer(updated, context={'request': request}).data)

    def delete(self, request, pk):
        post = BlogPost.objects.filter(pk=pk).first()
        if post is None:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)
        ok, error = delete_blog_post(post, request.user)
        if not ok:
            return Response({'detail': error}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
