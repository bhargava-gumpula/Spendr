import { Link } from 'react-router-dom'
import './Landing.css'

const STEPS = [
  {
    n: '1',
    title: 'Talk it through',
    body: "Answer a few quick questions about your idea, your team, and what you need funding for. No forms, no dropdowns — just a conversation.",
  },
  {
    n: '2',
    title: 'Get matched, not just listed',
    body: 'Claude ranks live grants.gov and SBIR.gov opportunities by real fit — and tells you where you qualify and where you might fall short.',
  },
  {
    n: '3',
    title: 'Know exactly what\'s next',
    body: "Pick any grant and get a plain-language walkthrough of eligibility, deadline, and how to actually apply.",
  },
]

export default function Landing() {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <div className="landing-brand">
          <div className="app-mark">G</div>
          <span>Granted</span>
        </div>
        <Link to="/chat" className="nav-cta">Talk to your advisor</Link>
      </nav>

      <header className="hero">
        <div className="hero-blob hero-blob-a" aria-hidden="true" />
        <div className="hero-blob hero-blob-b" aria-hidden="true" />
        <span className="eyebrow">AI Grants Advisor</span>
        <h1>Stop guessing which grants you qualify for.</h1>
        <p className="hero-sub">
          Tell Granted about your project in a real conversation. It matches you against
          live funding opportunities, checks your actual eligibility, and explains exactly
          how to apply — no legalese, no dead ends.
        </p>
        <Link to="/chat" className="hero-cta">
          Start the conversation
          <span aria-hidden="true">→</span>
        </Link>
        <p className="hero-note">No sign-up. No forms. Just tell it about your project.</p>
      </header>

      <section className="steps">
        {STEPS.map((s) => (
          <div className="step-card" key={s.n}>
            <div className="step-num">{s.n}</div>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </div>
        ))}
      </section>

      <section className="trust-strip">
        <span>Live from <strong>grants.gov</strong> &amp; <strong>SBIR.gov</strong></span>
        <span className="dot">·</span>
        <span>Never fabricates a grant — if it can't verify something, it says so</span>
      </section>

      <footer className="landing-footer">
        <span>Granted — built for FireHacks 2026, AI &amp; Research tracks</span>
      </footer>
    </div>
  )
}
