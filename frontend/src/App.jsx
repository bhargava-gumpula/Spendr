import { useState } from 'react'
import './App.css'

const EMPTY_PROFILE = {
  description: '',
  field: '',
  stage: '',
  team_size: '',
  location: '',
  funding_needed: '',
}

const QUALIFIES_LABEL = {
  yes: 'Qualifies',
  likely: 'Likely qualifies',
  unclear: 'Unclear — verify manually',
  no: 'May not qualify',
}

function formatDeadline(result) {
  if (result.deadline) {
    const d = new Date(result.deadline + 'T00:00:00')
    const formatted = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    const days = result.days_until_deadline
    if (days === null || days === undefined) return { text: `Closes ${formatted}`, kind: 'normal' }
    if (days < 0) return { text: `Closed ${formatted}`, kind: 'past' }
    if (days === 0) return { text: `Closes today`, kind: 'soon' }
    if (days <= 14) return { text: `Closes ${formatted} · in ${days}d`, kind: 'soon' }
    return { text: `Closes ${formatted} · in ${days}d`, kind: 'normal' }
  }
  if (result.deadline_display) return { text: result.deadline_display, kind: 'normal' }
  return { text: 'No deadline listed', kind: 'normal' }
}

function ScoreRing({ score }) {
  const r = 24
  const c = 2 * Math.PI * r
  const offset = c - (Math.max(0, Math.min(100, score)) / 100) * c
  return (
    <div className="score-ring">
      <svg viewBox="0 0 56 56">
        <circle className="track" cx="28" cy="28" r={r} />
        <circle
          className="fill"
          cx="28" cy="28" r={r}
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="num">{score}</div>
    </div>
  )
}

function GrantCard({ result, index }) {
  const [open, setOpen] = useState(false)
  const deadline = formatDeadline(result)
  const hasReasons = (result.fit_reasons?.length > 0 || result.gap_reasons?.length > 0)

  return (
    <article className="grant-card" style={{ animationDelay: `${Math.min(index, 8) * 45}ms` }}>
      <div className="grant-top">
        <div className="grant-title-wrap">
          <div className="grant-title">
            {result.url ? (
              <a href={result.url} target="_blank" rel="noreferrer">{result.title}</a>
            ) : result.title}
          </div>
          <div className="grant-meta">{result.agency || 'Unknown agency'} · {result.source}</div>
        </div>
        <ScoreRing score={result.match_score} />
      </div>

      <div className="pill-row">
        <span className={`pill qual-${result.qualifies}`}>
          <span className="pill-dot" />
          {QUALIFIES_LABEL[result.qualifies] || result.qualifies}
        </span>
        <span className={`pill deadline ${deadline.kind}`}>{deadline.text}</span>
        {result.funding_range && <span className="pill deadline">{result.funding_range}</span>}
        {result.confidence === 'low' && <span className="pill confidence-low">Low-confidence read</span>}
      </div>

      {hasReasons && (
        <>
          <button
            type="button"
            className={`reasons-toggle ${open ? 'open' : ''}`}
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
          >
            {open ? 'Hide details' : 'Why this match?'}
            <span className="chevron">▾</span>
          </button>
          <div className={`reasons-panel ${open ? 'open' : ''}`}>
            <div className="reasons-panel-inner">
              <div className="reasons">
                {result.fit_reasons?.length > 0 && (
                  <div className="reason-group fit">
                    <h4>Why it fits</h4>
                    <ul>{result.fit_reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
                  </div>
                )}
                {result.gap_reasons?.length > 0 && (
                  <div className="reason-group gap">
                    <h4>Worth checking</h4>
                    <ul>{result.gap_reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </article>
  )
}

function SkeletonList() {
  return (
    <div className="skeleton-list">
      {[0, 1, 2].map((i) => (
        <div className="skeleton-card" key={i} style={{ animationDelay: `${i * 120}ms` }} />
      ))}
    </div>
  )
}

function App() {
  const [profile, setProfile] = useState(EMPTY_PROFILE)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const update = (key) => (e) => setProfile((p) => ({ ...p, [key]: e.target.value }))

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const resp = await fetch('/api/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...profile, team_size: Number(profile.team_size) || 0 }),
      })
      if (!resp.ok) {
        const body = await resp.text()
        throw new Error(`Server error (${resp.status}): ${body.slice(0, 200)}`)
      }
      setResults(await resp.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-mark">G</div>
        <div>
          <h1>Granted</h1>
          <p>Your AI grants advisor — plain language in, matched funding out.</p>
        </div>
      </header>

      <form className="profile-form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="description">Project description</label>
          <textarea
            id="description"
            required
            placeholder="e.g. A student-built mobile app that helps low-income families find nearby food assistance programs via SMS alerts."
            value={profile.description}
            onChange={update('description')}
          />
        </div>

        <div className="field-row">
          <div className="field">
            <label htmlFor="field">Field</label>
            <input id="field" required placeholder="e.g. food security" value={profile.field} onChange={update('field')} />
          </div>
          <div className="field">
            <label htmlFor="stage">Stage</label>
            <input id="stage" required placeholder="e.g. prototype" value={profile.stage} onChange={update('stage')} />
          </div>
          <div className="field">
            <label htmlFor="team_size">Team size</label>
            <input id="team_size" type="number" min="1" required value={profile.team_size} onChange={update('team_size')} />
          </div>
        </div>

        <div className="field-row">
          <div className="field">
            <label htmlFor="location">Location</label>
            <input id="location" required placeholder="e.g. California, USA" value={profile.location} onChange={update('location')} />
          </div>
          <div className="field">
            <label htmlFor="funding_needed">Funding needed</label>
            <input id="funding_needed" required placeholder="e.g. $15,000" value={profile.funding_needed} onChange={update('funding_needed')} />
          </div>
        </div>

        <button className="submit-btn" type="submit" disabled={loading}>
          {loading && <span className="spinner" />}
          {loading ? 'Matching…' : 'Find my grants'}
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {loading && <SkeletonList />}

      {results && results.length === 0 && !loading && (
        <div className="empty-state">No live opportunities matched "{profile.field}" right now. Try broadening the field.</div>
      )}

      {results && results.length > 0 && !loading && (
        <section className="results">
          <div className="results-head">
            <h2>Matches</h2>
            <span>{results.length} ranked by fit</span>
          </div>
          {results.map((r, i) => <GrantCard key={`${r.source}-${r.external_id}`} result={r} index={i} />)}
        </section>
      )}
    </div>
  )
}

export default App
