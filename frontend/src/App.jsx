import { useEffect, useState } from 'react'
import Sidebar from './Sidebar.jsx'

export default function App() {
  const [me, setMe] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch('/api/me', { headers: { Accept: 'application/json' } })
      .then((response) => {
        if (response.status === 401) {
          window.location.assign('/login')
          return null
        }
        return response.ok ? response.json() : null
      })
      .then((body) => { if (!cancelled && body) setMe(body) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  return (
    <div className="shell">
      <header className="topbar">
        <span className="title">Social Media Harvester</span>
        {me && <span className="who">{me.email}</span>}
      </header>
      <Sidebar />
      <main className="content" />
    </div>
  )
}
