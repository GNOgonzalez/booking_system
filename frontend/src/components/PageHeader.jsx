export default function PageHeader({ title, intro, actions }) {
  return (
    <div className="page-header">
      <div>
        {title && <h1>{title}</h1>}
        {intro && <p className="page-intro">{intro}</p>}
      </div>
      {actions ? <div className="page-header-actions">{actions}</div> : null}
    </div>
  )
}
