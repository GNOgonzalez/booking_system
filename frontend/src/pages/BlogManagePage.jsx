import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch, apiUpload } from '../api.js'
import MarkdownPreview from '../components/MarkdownPreview.jsx'
import { blogImageHint, useUploadLimits } from '../hooks/useUploadLimits.js'

function formatWhen(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const emptyForm = {
  title: '',
  body: '',
  is_published: true,
  image: null,
  clear_image: false,
}

export default function BlogManagePage() {
  const limits = useUploadLimits()
  const imageHint = blogImageHint(limits)

  const [posts, setPosts] = useState([])
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => {
    apiFetch('/api/blog/manage/')
      .then(setPosts)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
  }

  const startEdit = (post) => {
    setEditingId(post.id)
    setForm({
      title: post.title,
      body: post.body,
      is_published: post.is_published,
      image: null,
      clear_image: false,
    })
    setError('')
    setMessage('')
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const data = new FormData()
      data.append('title', form.title.trim())
      data.append('body', form.body.trim())
      data.append('is_published', form.is_published ? 'true' : 'false')
      if (form.image) data.append('image', form.image)
      if (form.clear_image) data.append('clear_image', 'true')

      if (editingId) {
        await apiUpload(`/api/blog/${editingId}/`, data, { method: 'PATCH' })
        setMessage('Post updated.')
      } else {
        await apiUpload('/api/blog/manage/', data)
        setMessage('Post published.')
      }
      resetForm()
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const remove = async (post) => {
    if (!window.confirm(`Delete “${post.title}”?`)) return
    setError('')
    try {
      await apiFetch(`/api/blog/${post.id}/`, { method: 'DELETE' })
      if (editingId === post.id) resetForm()
      setMessage('Post deleted.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const editingPost = editingId ? posts.find((p) => p.id === editingId) : null

  return (
    <div>
      <h1>Blog posts</h1>
      <p className="page-intro">
        Publish announcements and photos on the home page for all members to see.
      </p>
      <p className="card-meta">
        <Link to="/">← Back to home</Link>
      </p>

      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form onSubmit={submit} className="card" style={{ marginBottom: '1.5rem' }}>
        <h2>{editingId ? 'Edit post' : 'New post'}</h2>
        <div className="field">
          <label>Title</label>
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
            maxLength={200}
          />
        </div>
        <div className="field">
          <label>Body</label>
          <textarea
            value={form.body}
            onChange={(e) => setForm({ ...form, body: e.target.value })}
            rows={6}
            required
          />
          <p className="card-meta">
            Formatting: **bold**, *italic*, [links](https://…), - lists, and blank lines for paragraphs.
          </p>
          <MarkdownPreview source={form.body} />
        </div>
        <div className="field">
          <label>Photo (optional)</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setForm({ ...form, image: e.target.files?.[0] || null, clear_image: false })}
          />
          {imageHint && <p className="card-meta">{imageHint}</p>}
          {editingPost?.image_url && !form.clear_image && (
            <div className="blog-manage-preview">
              <img src={editingPost.image_url} alt="" className="blog-post-image blog-post-image--small" />
              <button
                type="button"
                className="ghost"
                onClick={() => setForm({ ...form, image: null, clear_image: true })}
              >
                Remove photo
              </button>
            </div>
          )}
        </div>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={form.is_published}
            onChange={(e) => setForm({ ...form, is_published: e.target.checked })}
          />
          Published (visible on home page)
        </label>
        <div className="form-actions">
          <button type="submit" disabled={saving}>
            {saving ? 'Saving…' : editingId ? 'Save changes' : 'Publish post'}
          </button>
          {editingId && (
            <button type="button" className="secondary" onClick={resetForm}>
              Cancel edit
            </button>
          )}
        </div>
      </form>

      <h2>Your posts</h2>
      {posts.map((post) => (
        <div key={post.id} className="card blog-manage-item">
          <div className="blog-manage-item-header">
            <div>
              <div className="card-title">{post.title}</div>
              <div className="card-meta">
                {formatWhen(post.created_at)}
                {!post.is_published && ' · Draft'}
              </div>
            </div>
            <div className="blog-manage-item-actions">
              <button type="button" className="secondary" onClick={() => startEdit(post)}>
                Edit
              </button>
              <button type="button" className="ghost" onClick={() => remove(post)}>
                Delete
              </button>
            </div>
          </div>
          {post.image_url && (
            <img src={post.image_url} alt="" className="blog-post-image blog-post-image--small" />
          )}
          <p className="blog-post-body blog-post-body--preview">{post.body}</p>
        </div>
      ))}
      {!posts.length && <p className="card-meta">No posts yet.</p>}
    </div>
  )
}
