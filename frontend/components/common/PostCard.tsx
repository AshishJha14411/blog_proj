import Link from 'next/link'
import { Post } from '@/services/postService'

interface PostCardProps {
    post: Post;
}


export default function PostCard({post}: PostCardProps){
    return (
    <Link href={`/posts/${post.id}`}>
      <div className="flex h-full flex-col justify-between rounded-lg bg-background-alt p-6 shadow-md transition-transform duration-200 hover:-translate-y-1">
        <div>
          <h3 className="mb-2 text-xl font-bold text-text">{post.title}</h3>
          <p className="mb-4 text-text-light line-clamp-3">
            {post.content}
          </p>
        </div>
        <div className="text-sm text-text-light">
          <span>By {post.user.username}</span>
          <span className="mx-2">•</span>
          <span>{new Date(post.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    </Link>
  );
}