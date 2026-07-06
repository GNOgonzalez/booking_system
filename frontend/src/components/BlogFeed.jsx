import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { MarkdownBody } from './MarkdownPreview.jsx'

function formatWhen(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function BlogFeed({ canManage }) {
  const [posts, setPosts] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch('/api/blog/')
      .then(setPosts)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="blog-feed">
      <div className="blog-feed-header">
        <h2>Studio updates</h2>
        {canManage && (
          <Link to="/blog/manage" className="btn secondary">
            Manage posts
          </Link>
        )}
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <p className="card-meta">Loading…</p>}

      {posts.map((post) => (
        <article key={post.id} className="card blog-post">
          {post.image_url && (
            <img src={post.image_url} alt="" className="blog-post-image" />
          )}
          <div className="card-title">{post.title}</div>
          <div className="card-meta">
            {post.author_name} · {formatWhen(post.created_at)}
          </div>
          {post.body_html ? (
            <MarkdownBody html={post.body_html} className="blog-post-body" />
          ) : (
            <div className="blog-post-body">{post.body}</div>
          )}
        </article>
      ))}

      {!loading && !posts.length && !error && (
        <p className="card-meta">No announcements yet.</p>
      )}
    </section>
  )
}
