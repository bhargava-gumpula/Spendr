import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import DotMark from '../components/DotMark'
import './Chat.css'

const GREETING = "Hi, I'm your grants advisor. Let's start simple — what are you building?"

const QUALIFIES_LABEL = {
  yes: 'Qualifies',
  likely: 'Likely qualifies',
  unclear: 'Unclear — verify manually',
  no: 'May not qualify',
}

const SOURCE_LABEL = {
  'grants.gov': 'grants.gov',
  'sbir.gov': 'sbir.gov',
  web: 'found via web search',
}

function formatDeadline(result) {
  if (result.deadline) {
    const d = new Date(result.deadline + 'T00:00:00')
    const formatted = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    const days = result.days_until_deadline
    if (days === null || days === undefined) return { text: `Closes ${formatted}`, kind: 'normal' }
    if (days < 0) return { text: `Closed ${formatted}`, kind: 'past' }
    if (days === 0) return { text: 'Closes today', kind: 'soon' }
    if (days <= 14) return { text: `Closes ${formatted} · in ${days}d`, kind: 'soon' }
    return { text: `Closes ${formatted} · in ${days}d`, kind: 'normal' }
  }
  if (result.deadline_display) return { text: result.deadline_display, kind: 'normal' }
  return { text: 'No deadline listed', kind: 'normal' }
}

function VerifyLink({ url }) {
  return url ? (
    <a className="verify-link" href={url} target="_blank" rel="noreferrer">
      View original listing <span aria-hidden="true">↗</span>
    </a>
  ) : (
    <span className="verify-link verify-link-missing">No direct link found — verify with the agency directly</span>
  )
}

function MatchCard({ result, onAskApply }) {
  const deadline = formatDeadline(result)
  return (
    <div className="match-card">
      <div className="match-top">
        <div>
          <div className="match-title">{result.title}</div>
          <div className="match-meta">{result.agency || 'Unknown agency'} · {SOURCE_LABEL[result.source] || result.source}</div>
        </div>
        <div className="score-chip">{result.match_score}</div>
      </div>
      <div className="pill-row">
        <span className={`pill qual-${result.qualifies}`}><span className="pill-dot" />{QUALIFIES_LABEL[result.qualifies] || result.qualifies}</span>
        <span className={`pill deadline ${deadline.kind}`}>{deadline.text}</span>
        {result.funding_range && <span className="pill deadline">{result.funding_range}</span>}
      </div>
      <VerifyLink url={result.url} />
      <button type="button" className="ask-apply-btn" onClick={() => onAskApply(result)}>
        How do I apply?
      </button>
    </div>
  )
}

function ExplanationCard({ explanation }) {
  return (
    <div className="explain-card">
      <div className="explain-head">{explanation.grant.title}</div>
      <div className="explain-meta-row">
        {explanation.qualifies && (
          <span className={`pill qual-${explanation.qualifies}`}><span className="pill-dot" />{QUALIFIES_LABEL[explanation.qualifies] || explanation.qualifies}</span>
        )}
        {explanation.deadline_display && <span className="pill deadline">{explanation.deadline_display}</span>}
        {explanation.funding_range && <span className="pill deadline">{explanation.funding_range}</span>}
      </div>
      <VerifyLink url={explanation.grant.url} />
      {explanation.steps?.length > 0 && (
        <ol className="explain-steps">
          {explanation.steps.map((s, i) => <li key={i}>{s}</li>)}
        </ol>
      )}
      {(explanation.confidence === 'low' || explanation.fetch_status !== 'ok') && (
        <div className="explain-low-confidence">
          {explanation.fetch_status !== 'ok'
            ? "Couldn't fetch this grant's requirements page — verify details on the official listing before applying."
            : 'Low-confidence read on this one — double check the details on the official listing.'}
        </div>
      )}
    </div>
  )
}

export default function Chat() {
  const [messages, setMessages] = useState([{ role: 'assistant', content: GREETING }])
  const [knownGrants, setKnownGrants] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeGrant, setActiveGrant] = useState(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  function mergeKnownGrants(matches) {
    if (!matches?.length) return
    setKnownGrants((prev) => {
      const next = [...prev]
      for (const m of matches) {
        if (!next.some((g) => g.source === m.source && g.external_id === m.external_id)) {
          next.push({ source: m.source, external_id: m.external_id, title: m.title, url: m.url })
        }
      }
      return next
    })
  }

  async function sendMessage(text) {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    const userMsg = { role: 'user', content: trimmed }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: nextMessages.map(({ role, content }) => ({ role, content })),
          known_grants: knownGrants,
          active_grant: activeGrant,
        }),
      })
      if (!resp.ok) {
        const body = await resp.text()
        throw new Error(`Server error (${resp.status}): ${body.slice(0, 200)}`)
      }
      const data = await resp.json()
      mergeKnownGrants(data.matches)
      setActiveGrant(data.active_grant || null)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply, matches: data.matches, explanation: data.explanation }])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    sendMessage(input)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="app-mark-link">
          <DotMark className="app-mark" />
        </Link>
        <div>
          <h1>Granted</h1>
          <p>Your AI grants advisor</p>
        </div>
      </header>

      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m, i) => (
          <div className={`msg-row ${m.role}`} key={i}>
            {m.matches?.length > 0 || m.explanation ? (
              <div className="msg-block">
                <div className="msg-bubble">{m.content}</div>
                {m.matches?.length > 0 && (
                  <div className="match-cards">
                    {m.matches.map((r) => (
                      <MatchCard key={`${r.source}-${r.external_id}`} result={r} onAskApply={(g) => sendMessage(`How do I apply to "${g.title}"?`)} />
                    ))}
                  </div>
                )}
                {m.explanation && <ExplanationCard explanation={m.explanation} />}
              </div>
            ) : (
              <div className="msg-bubble">{m.content}</div>
            )}
          </div>
        ))}

        {loading && (
          <div className="msg-row assistant">
            <div className="msg-bubble">
              <div className="typing-dots"><span /><span /><span /></div>
            </div>
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <textarea
          rows={1}
          placeholder="Type your answer…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button type="submit" className="composer-send" disabled={loading || !input.trim()} aria-label="Send">
          ↑
        </button>
      </form>
    </div>
  )
}
