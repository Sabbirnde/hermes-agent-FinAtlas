import React, { useState, useRef, useEffect } from 'react'
import './index.css'

// ── Types ──────────────────────────────────────────────────────────────────

interface Country {
  code: string
  name: string
  flag_emoji: string
  currency_symbol: string
  currency_code: string
  is_live: boolean
}

interface PipelineStage {
  id: string
  label: string
  status: 'pending' | 'running' | 'done' | 'failed'
}

interface ProductResult {
  rank: number
  institution: string
  product_name: string
  rate_display: string
  rate_type?: string
  is_islamic?: boolean
  monthly_installment?: number
  total_cost?: number
  return_amount?: number
  known_fees?: number
  eligibility_classification?: string
  verification_status: string
  confidence: number
  source_url?: string
  checked_at?: string
  why_it_ranks: string
  collateral_required?: boolean
}

// ── Constants ──────────────────────────────────────────────────────────────

const COUNTRIES: Country[] = [
  { code: 'BD', name: 'Bangladesh', flag_emoji: '🇧🇩', currency_symbol: '৳', currency_code: 'BDT', is_live: true },
  { code: 'IN', name: 'India', flag_emoji: '🇮🇳', currency_symbol: '₹', currency_code: 'INR', is_live: false },
  { code: 'PK', name: 'Pakistan', flag_emoji: '🇵🇰', currency_symbol: 'Rs', currency_code: 'PKR', is_live: false },
  { code: 'NP', name: 'Nepal', flag_emoji: '🇳🇵', currency_symbol: 'Rs', currency_code: 'NPR', is_live: false },
  { code: 'MY', name: 'Malaysia', flag_emoji: '🇲🇾', currency_symbol: 'RM', currency_code: 'MYR', is_live: false },
  { code: 'ID', name: 'Indonesia', flag_emoji: '🇮🇩', currency_symbol: 'Rp', currency_code: 'IDR', is_live: false },
  { code: 'NG', name: 'Nigeria', flag_emoji: '🇳🇬', currency_symbol: '₦', currency_code: 'NGN', is_live: false },
  { code: 'SA', name: 'Saudi Arabia', flag_emoji: '🇸🇦', currency_symbol: '﷼', currency_code: 'SAR', is_live: false },
]

const PIPELINE_STAGES: PipelineStage[] = [
  { id: 'intent', label: 'Intent', status: 'pending' },
  { id: 'planning', label: 'Planning', status: 'pending' },
  { id: 'discovery', label: 'Discovery', status: 'pending' },
  { id: 'research', label: 'Research', status: 'pending' },
  { id: 'extraction', label: 'Extraction', status: 'pending' },
  { id: 'evidence', label: 'Evidence', status: 'pending' },
  { id: 'verification', label: 'Verification', status: 'pending' },
  { id: 'calculation', label: 'Calculation', status: 'pending' },
  { id: 'eligibility', label: 'Eligibility', status: 'pending' },
  { id: 'ranking', label: 'Ranking', status: 'pending' },
]

const EXAMPLE_QUERIES = [
  'I need a personal loan of ৳5,00,000 for 5 years. Find the cheapest option.',
  'Which bank has the highest FDR rate for 1 year in Bangladesh?',
  'I have ৳5 lakh. Where should I keep it to get the best return?',
  'Find home loans in Bangladesh without collateral.',
  'I earn ৳80,000/month. Which personal loans could I qualify for?',
]

const RANK_EMOJI = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']

// ── Utility Functions ─────────────────────────────────────────────────────

function formatCurrency(amount: number, symbol: string): string {
  if (amount >= 10_000_000) return `${symbol}${(amount / 10_000_000).toFixed(2)} Cr`
  if (amount >= 100_000) return `${symbol}${(amount / 100_000).toFixed(2)} L`
  return `${symbol}${amount.toLocaleString('en-IN')}`
}

// ── Components ─────────────────────────────────────────────────────────────

function Nav({ selectedCountry, onCountryChange }: { selectedCountry: Country; onCountryChange: () => void }) {
  return (
    <nav className="nav">
      <a href="/" className="nav-logo">
        <div className="nav-logo-icon">CA</div>
        <span className="nav-logo-text">COMPARE <span>AI</span></span>
      </a>
      <div className="nav-links">
        <button className="nav-country-pill" onClick={onCountryChange}>
          <span>{selectedCountry.flag_emoji}</span>
          <span>{selectedCountry.name}</span>
          <span style={{ fontSize: '10px', opacity: 0.6 }}>▾</span>
        </button>
      </div>
    </nav>
  )
}

function CountryGrid({ onSelect }: { onSelect: (c: Country) => void }) {
  return (
    <div className="country-section">
      <p className="section-label">Select your market</p>
      <div className="country-grid">
        {COUNTRIES.map((c) => (
          <button
            key={c.code}
            className={`country-card ${c.is_live ? 'live' : 'coming-soon'}`}
            onClick={() => c.is_live && onSelect(c)}
          >
            <span className="country-flag">{c.flag_emoji}</span>
            <span className="country-name">{c.name}</span>
            <span className={`country-status ${c.is_live ? 'live' : 'soon'}`}>
              {c.is_live ? 'Live' : 'Coming soon'}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

function PipelineSidebar({
  stages,
  stats,
}: {
  stages: PipelineStage[]
  stats: { sources: number; products: number; verified: number; conflicts: number }
}) {
  return (
    <aside className="pipeline-sidebar">
      <p className="pipeline-title">Research Pipeline</p>
      <div className="pipeline-stages">
        {stages.map((stage) => (
          <div
            key={stage.id}
            className={`pipeline-stage ${stage.status === 'done' ? 'completed' : stage.status === 'running' ? 'active' : ''}`}
          >
            <div className={`stage-icon ${stage.status === 'done' ? 'done' : stage.status === 'running' ? 'running' : 'pending'}`}>
              {stage.status === 'done' ? '✓' : stage.status === 'running' ? '⟳' : '·'}
            </div>
            <span className="stage-name">{stage.label}</span>
          </div>
        ))}
      </div>

      <div className="research-stats">
        <div className="stat-pill">
          <span className="stat-value">{stats.sources}</span>
          <span className="stat-label">Sources</span>
        </div>
        <div className="stat-pill">
          <span className="stat-value">{stats.products}</span>
          <span className="stat-label">Products</span>
        </div>
        <div className="stat-pill">
          <span className="stat-value" style={{ color: 'var(--accent-primary)' }}>{stats.verified}</span>
          <span className="stat-label">Verified</span>
        </div>
        <div className="stat-pill">
          <span className="stat-value" style={{ color: stats.conflicts > 0 ? 'var(--accent-danger)' : 'var(--text-primary)' }}>
            {stats.conflicts}
          </span>
          <span className="stat-label">Conflicts</span>
        </div>
      </div>
    </aside>
  )
}

function ProductCard({ product, symbol }: { product: ProductResult; symbol: string }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={`product-card rank-${product.rank} animate-fade-in`}>
      <div className="product-card-header">
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
          <span className="product-rank">{RANK_EMOJI[product.rank - 1] || `#${product.rank}`}</span>
          <div>
            <div className="product-institution">{product.institution}</div>
            <div className="product-name">{product.product_name}</div>
          </div>
        </div>
        <div className="product-badges">
          {product.verification_status === 'verified' && (
            <span className="badge badge-verified">✓ Verified</span>
          )}
          {product.is_islamic && (
            <span className="badge badge-islamic">☪ Islamic</span>
          )}
          {product.verification_status === 'conflicting' && (
            <span className="badge badge-conflict">⚠ Conflict</span>
          )}
        </div>
      </div>

      <div className="product-metrics">
        <div className="metric-item">
          <span className="metric-label">Published Rate</span>
          <span className="metric-value gold">{product.rate_display}</span>
          {product.rate_type && (
            <span className="metric-note">{product.rate_type}</span>
          )}
        </div>

        {product.monthly_installment && (
          <div className="metric-item">
            <span className="metric-label">Est. Monthly</span>
            <span className="metric-value calculated">{formatCurrency(product.monthly_installment, symbol)}</span>
            <span className="metric-note">Calculated*</span>
          </div>
        )}

        {product.total_cost && (
          <div className="metric-item">
            <span className="metric-label">Est. Total Cost</span>
            <span className="metric-value">{formatCurrency(product.total_cost, symbol)}</span>
            <span className="metric-note">Calculated*</span>
          </div>
        )}

        {product.return_amount && (
          <div className="metric-item">
            <span className="metric-label">Est. Return</span>
            <span className="metric-value teal">{formatCurrency(product.return_amount, symbol)}</span>
            <span className="metric-note">Calculated*</span>
          </div>
        )}

        {product.known_fees !== undefined && product.known_fees !== null && (
          <div className="metric-item">
            <span className="metric-label">Known Fees</span>
            <span className="metric-value">{product.known_fees === 0 ? 'None listed' : formatCurrency(product.known_fees, symbol)}</span>
          </div>
        )}

        {product.eligibility_classification && (
          <div className="metric-item">
            <span className="metric-label">Eligibility</span>
            <span className="metric-value" style={{
              color: product.eligibility_classification === 'likely_eligible' ? 'var(--accent-primary)'
                : product.eligibility_classification === 'likely_not_eligible' ? 'var(--accent-danger)'
                : 'var(--accent-secondary)',
              fontSize: '13px'
            }}>
              {product.eligibility_classification?.replace(/_/g, ' ')}
            </span>
          </div>
        )}

        {product.collateral_required !== undefined && product.collateral_required !== null && (
          <div className="metric-item">
            <span className="metric-label">Collateral</span>
            <span className="metric-value" style={{ fontSize: '13px', color: product.collateral_required ? 'var(--text-secondary)' : 'var(--accent-primary)' }}>
              {product.collateral_required ? 'Required' : 'Not required'}
            </span>
          </div>
        )}
      </div>

      <div className="product-footer">
        <div className="product-why">
          <strong>Why it ranks:</strong> {product.why_it_ranks}
        </div>
        <div className="product-source">
          {product.source_url && (
            <a href={product.source_url} target="_blank" rel="noopener noreferrer" className="source-link">
              Official source ↗
            </a>
          )}
          {product.checked_at && (
            <span className="source-date">Checked: {product.checked_at}</span>
          )}
        </div>
      </div>
    </div>
  )
}

function ProductSkeleton() {
  return (
    <div className="product-card" style={{ opacity: 0.6 }}>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', alignItems: 'flex-start' }}>
        <div className="skeleton" style={{ width: 32, height: 32, borderRadius: '50%' }} />
        <div style={{ flex: 1 }}>
          <div className="skeleton" style={{ height: 16, width: '60%', marginBottom: 6 }} />
          <div className="skeleton" style={{ height: 12, width: '40%' }} />
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        {[0, 1, 2].map(i => (
          <div key={i}>
            <div className="skeleton" style={{ height: 10, width: '60%', marginBottom: 6 }} />
            <div className="skeleton" style={{ height: 18, width: '80%' }} />
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────

export default function App() {
  const [view, setView] = useState<'home' | 'research'>('home')
  const [selectedCountry, setSelectedCountry] = useState<Country>(COUNTRIES[0])
  const [showCountryPicker, setShowCountryPicker] = useState(false)
  const [query, setQuery] = useState('')
  const [isResearching, setIsResearching] = useState(false)
  const [stages, setStages] = useState<PipelineStage[]>(PIPELINE_STAGES.map(s => ({ ...s })))
  const [products, setProducts] = useState<ProductResult[]>([])
  const [stats, setStats] = useState({ sources: 0, products: 0, verified: 0, conflicts: 0 })
  const [answerText, setAnswerText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const symbol = selectedCountry.currency_symbol

  const advanceStage = (stageId: string, status: 'running' | 'done') => {
    setStages(prev => prev.map(s => s.id === stageId ? { ...s, status } : s))
  }

  const simulateResearch = async (q: string) => {
    setIsResearching(true)
    setProducts([])
    setStats({ sources: 0, products: 0, verified: 0, conflicts: 0 })
    setAnswerText('')
    setStages(PIPELINE_STAGES.map(s => ({ ...s, status: 'pending' as const })))
    setView('research')

    const stageFlow: Array<[string, number, Partial<typeof stats>]> = [
      ['intent', 600, {}],
      ['planning', 800, {}],
      ['discovery', 1000, { sources: 8 }],
      ['research', 2500, { sources: 12, products: 6 }],
      ['extraction', 1200, { products: 9 }],
      ['evidence', 900, { verified: 7 }],
      ['verification', 700, { conflicts: 1 }],
      ['calculation', 400, {}],
      ['eligibility', 300, {}],
      ['ranking', 200, {}],
    ]

    for (const [id, delay, statUpdate] of stageFlow) {
      advanceStage(id, 'running')
      await new Promise(r => setTimeout(r, delay))
      advanceStage(id, 'done')
      if (Object.keys(statUpdate).length) {
        setStats(prev => ({ ...prev, ...statUpdate }))
      }
    }

    // Mock results
    setProducts([
      {
        rank: 1,
        institution: 'BRAC Bank PLC',
        product_name: 'Personal Loan',
        rate_display: '11.50% p.a.',
        rate_type: 'Variable',
        is_islamic: false,
        monthly_installment: 10889,
        total_cost: 653340,
        known_fees: 5000,
        eligibility_classification: 'likely_eligible',
        verification_status: 'verified',
        confidence: 0.93,
        source_url: 'https://www.bracbank.com/personal/loans/personal-loan',
        checked_at: '4 August 2026',
        why_it_ranks: 'Lowest estimated total cost among verified products. Rate confirmed from official product page.',
        collateral_required: false,
      },
      {
        rank: 2,
        institution: 'Dutch-Bangla Bank PLC',
        product_name: 'Personal Loan',
        rate_display: '12.00% p.a.',
        rate_type: 'Fixed',
        is_islamic: false,
        monthly_installment: 11122,
        total_cost: 667320,
        known_fees: 3000,
        eligibility_classification: 'likely_eligible',
        verification_status: 'verified',
        confidence: 0.91,
        source_url: 'https://www.dutchbanglabank.com/personal-banking/loans/personal-loan',
        checked_at: '4 August 2026',
        why_it_ranks: 'Fixed rate provides payment certainty. Lower processing fee offsets slightly higher rate.',
        collateral_required: false,
      },
      {
        rank: 3,
        institution: 'The City Bank PLC',
        product_name: 'City Personal Loan',
        rate_display: 'From 12.50% p.a.',
        rate_type: 'Variable',
        is_islamic: false,
        monthly_installment: 11359,
        total_cost: 681540,
        known_fees: 4500,
        eligibility_classification: 'possibly_eligible',
        verification_status: 'partial',
        confidence: 0.72,
        source_url: 'https://www.thecitybank.com/personal-banking/loans/personal-loan',
        checked_at: '4 August 2026',
        why_it_ranks: 'Published rate is a minimum ("from"). Actual rate depends on customer profile.',
        collateral_required: false,
      },
    ])

    setAnswerText(q)
    setIsResearching(false)
  }

  const handleSubmit = () => {
    if (!query.trim()) return
    simulateResearch(query.trim())
    setQuery('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const selectExample = (q: string) => {
    setQuery(q)
    textareaRef.current?.focus()
  }

  // ── Home View ─────────────────────────────────────────────────────────────

  if (view === 'home') {
    return (
      <div className="app-layout">
        <Nav selectedCountry={selectedCountry} onCountryChange={() => setShowCountryPicker(true)} />

        <main>
          {/* Hero */}
          <section className="hero">
            <div className="hero-badge">AI Financial Research · Evidence-Backed · Official Sources</div>
            <h1 className="hero-title">
              Research any financial product,<br />
              <span className="highlight">worldwide.</span>
            </h1>
            <p className="hero-subtitle">
              Ask COMPARE AI about loans, savings, FDR, DPS, and more.
              It researches official sources, verifies the information,
              calculates costs, and ranks the best matches.
            </p>

            {/* Search */}
            <div className="search-container">
              <div className="search-bar">
                <textarea
                  ref={textareaRef}
                  className="search-input"
                  placeholder={`Ask about financial products in ${selectedCountry.name}...`}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                />
                <button className="search-btn" onClick={handleSubmit}>
                  <span>Research</span>
                  <span>→</span>
                </button>
              </div>

              {/* Example queries */}
              <div style={{ marginTop: '16px', display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
                {EXAMPLE_QUERIES.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => selectExample(q)}
                    style={{
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-full)',
                      color: 'var(--text-secondary)',
                      fontSize: '12px',
                      padding: '6px 12px',
                      cursor: 'pointer',
                      transition: 'all 200ms ease',
                      fontFamily: 'var(--font-ui)',
                    }}
                    onMouseEnter={e => {
                      (e.target as HTMLElement).style.borderColor = 'var(--accent-primary)'
                      ;(e.target as HTMLElement).style.color = 'var(--accent-primary)'
                    }}
                    onMouseLeave={e => {
                      (e.target as HTMLElement).style.borderColor = 'var(--border-subtle)'
                      ;(e.target as HTMLElement).style.color = 'var(--text-secondary)'
                    }}
                  >
                    {q.length > 60 ? q.slice(0, 60) + '…' : q}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Country Grid */}
          <CountryGrid onSelect={(c) => { setSelectedCountry(c); setView('research') }} />

          {/* How it works */}
          <section style={{ padding: '0 24px 64px', maxWidth: '900px', margin: '0 auto' }}>
            <p className="section-label" style={{ textAlign: 'center', marginBottom: '24px' }}>How COMPARE AI works</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              {[
                { icon: '🔍', title: 'Research', desc: 'Searches official bank websites, rate sheets, and regulatory sources' },
                { icon: '✓', title: 'Verify', desc: 'Cross-checks information across multiple sources and flags conflicts' },
                { icon: '📊', title: 'Calculate', desc: 'Deterministic EMI and return calculations from published rates' },
                { icon: '🏆', title: 'Rank', desc: 'Transparent ranking based on your priorities with plain-English explanations' },
              ].map(step => (
                <div key={step.title} style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                  textAlign: 'center',
                }}>
                  <div style={{ fontSize: '28px', marginBottom: '12px' }}>{step.icon}</div>
                  <div style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' }}>{step.title}</div>
                  <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{step.desc}</div>
                </div>
              ))}
            </div>
          </section>
        </main>

        {/* Disclaimer */}
        <div className="disclaimer-banner">
          COMPARE AI provides financial product information for research purposes only.
          It does not provide financial advice, guarantee loan approval, or guarantee returns.
          Always verify with the financial institution before making decisions.
        </div>
      </div>
    )
  }

  // ── Research View ─────────────────────────────────────────────────────────

  return (
    <div className="app-layout">
      <Nav selectedCountry={selectedCountry} onCountryChange={() => setShowCountryPicker(true)} />

      <div className="research-layout">
        <PipelineSidebar stages={stages} stats={stats} />

        <div className="results-panel">
          {/* Results header */}
          <div className="results-header">
            <div>
              <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {isResearching ? '⟳ Researching…' : products.length > 0 ? `${products.length} matches found` : 'Ready'}
              </span>
              {answerText && (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  "{answerText.slice(0, 80)}{answerText.length > 80 ? '…' : ''}"
                </div>
              )}
            </div>
            <button
              onClick={() => setView('home')}
              style={{
                background: 'none',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-full)',
                color: 'var(--text-secondary)',
                fontSize: '12px',
                padding: '4px 12px',
                cursor: 'pointer',
                fontFamily: 'var(--font-ui)',
              }}
            >
              ← New search
            </button>
          </div>

          {/* Results content */}
          <div className="results-content">
            {isResearching && products.length === 0 && (
              <>
                <ProductSkeleton />
                <ProductSkeleton />
                <ProductSkeleton />
              </>
            )}

            {!isResearching && products.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon">🔍</div>
                <div className="empty-title">Ready to research</div>
                <div className="empty-subtitle">
                  Ask about any financial product in {selectedCountry.name}.
                  COMPARE AI will search official sources and return verified results.
                </div>
              </div>
            )}

            {products.map(product => (
              <ProductCard key={`${product.rank}-${product.institution}`} product={product} symbol={symbol} />
            ))}

            {products.length > 0 && (
              <div style={{
                background: 'rgba(255,107,53,0.08)',
                border: '1px solid rgba(255,107,53,0.2)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 16px',
                fontSize: '12px',
                color: 'var(--text-secondary)',
                lineHeight: 1.6,
                marginTop: '8px',
              }}>
                ⚠️ <strong style={{ color: 'var(--text-primary)' }}>Important:</strong>{' '}
                Monthly payment and total cost figures marked "Calculated" are computed from the institution's
                published rate using standard formulas. They are not official loan quotations. Actual pricing,
                approval, and terms depend entirely on the financial institution.
              </div>
            )}
          </div>

          {/* Chat input */}
          <div className="chat-input-area">
            <div className="chat-input-bar">
              <textarea
                className="chat-textarea"
                placeholder="Ask about any financial product…"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />
              <button className="send-btn" onClick={handleSubmit} title="Research">
                →
              </button>
            </div>
          </div>

          <div className="disclaimer-banner">
            COMPARE AI · Evidence-backed financial research · Not financial advice
          </div>
        </div>
      </div>
    </div>
  )
}
