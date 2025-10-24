
import Link from 'next/link';
import { Post } from '@/services/postService';

interface PostCardProps {
  post: Post;
}

export default function PostCard({ post }: PostCardProps) {
  // --- Conditional Logic for Status ---
  let statusText = '';
  let statusColor = '';
  let cardBorderColor = 'border-transparent'; // Default border

  if (post.is_flagged) {
    statusText = 'Under Review';
    statusColor = 'bg-yellow-100 text-yellow-800';
    cardBorderColor = 'border-yellow-400'; // Highlight flagged posts
  } else if (!post.is_published) {
    statusText = 'Draft';
    statusColor = 'bg-gray-100 text-gray-800';
    cardBorderColor = 'border-gray-300'; // Differentiate drafts
  }
  // Published posts will have no status text and a transparent border.
  // console.log(post)
  return (
    <Link href={`/userStory/${post.id}`}>
      {/* The outer div now has a conditional border */}
      <div
        className={`flex h-full flex-col justify-between rounded-lg border-2 bg-background-alt p-6 shadow-md transition-all duration-200 hover:-translate-y-1 ${cardBorderColor}`}
      >
        <div>
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-xl font-bold text-text">{post.title}</h3>
            {/* The Status Badge: only renders if statusText is not empty */}
            {statusText && (
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColor}`}>
                {statusText}
              </span>
            )}
          </div>
          <p className="mb-4 text-text-light line-clamp-3">{post.content}</p>
        </div>
        <div className="mb-4 flex flex-wrap gap-2">
          {post.tags.map((tag) => (
            <span key={tag.id} className="text-xs font-medium bg-primary/10 text-primary px-2 py-1 rounded-full">
              {tag.name}
            </span>
          ))}
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
