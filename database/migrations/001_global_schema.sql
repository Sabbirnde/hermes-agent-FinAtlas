-- ══════════════════════════════════════════════════════════════════════════
-- COMPARE AI — Global Database Schema (PostgreSQL)
-- ══════════════════════════════════════════════════════════════════════════

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Countries ─────────────────────────────────────────────────────────────
CREATE TABLE countries (
    country_code        VARCHAR(2)    PRIMARY KEY,  -- ISO 3166-1 alpha-2
    country_name        VARCHAR(100)  NOT NULL,
    currency_code       CHAR(3)       NOT NULL,     -- ISO 4217
    currency_symbol     VARCHAR(8)    NOT NULL,
    currency_position   VARCHAR(6)    NOT NULL DEFAULT 'before', -- before | after
    is_live             BOOLEAN       NOT NULL DEFAULT FALSE,
    launched_at         DATE,
    primary_language    CHAR(2),                    -- ISO 639-1
    languages           TEXT[]        DEFAULT '{"en"}',
    is_rtl              BOOLEAN       NOT NULL DEFAULT FALSE,
    flag_emoji          VARCHAR(8),
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ── Regulators ────────────────────────────────────────────────────────────
CREATE TABLE regulators (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code        VARCHAR(2)    NOT NULL REFERENCES countries(country_code),
    name                VARCHAR(200)  NOT NULL,
    abbreviation        VARCHAR(20),
    website_url         VARCHAR(500),
    type                VARCHAR(50),  -- central_bank | securities_comm | mra | ...
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ── Institutions ──────────────────────────────────────────────────────────
CREATE TABLE institutions (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code        VARCHAR(2)    NOT NULL REFERENCES countries(country_code),
    name                VARCHAR(300)  NOT NULL,
    slug                VARCHAR(100)  NOT NULL,
    type                VARCHAR(50)   NOT NULL, -- bank | nbfi | mfi | cooperative | insurer
    subtype             VARCHAR(50),             -- state_owned | private | islamic | foreign
    is_islamic          BOOLEAN       NOT NULL DEFAULT FALSE,
    official_website    VARCHAR(500),
    logo_url            VARCHAR(500),
    regulator_id        UUID          REFERENCES regulators(id),
    is_active           BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE(country_code, slug)
);

-- ── Products ──────────────────────────────────────────────────────────────
CREATE TABLE products (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      UUID          NOT NULL REFERENCES institutions(id),
    country_code        VARCHAR(2)    NOT NULL REFERENCES countries(country_code),
    product_name        VARCHAR(300)  NOT NULL,
    category            VARCHAR(50)   NOT NULL, -- loan | savings | deposit | investment | insurance
    subcategory         VARCHAR(50),             -- personal_loan | fdr | dps | home_loan | ...
    is_islamic          BOOLEAN       NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ── Product Versions (snapshot per research run) ──────────────────────────
CREATE TABLE product_versions (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID          NOT NULL REFERENCES products(id),
    version_number      INTEGER       NOT NULL DEFAULT 1,
    data                JSONB         NOT NULL DEFAULT '{}', -- full normalized schema
    researched_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    research_run_id     UUID,
    is_current          BOOLEAN       NOT NULL DEFAULT TRUE,
    overall_confidence  FLOAT         CHECK (overall_confidence BETWEEN 0 AND 1),
    verification_status VARCHAR(50)   DEFAULT 'unverified' -- verified|partial|conflicting|stale
);

-- ── Evidence Records ──────────────────────────────────────────────────────
CREATE TABLE evidence_records (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    product_version_id  UUID          NOT NULL REFERENCES product_versions(id),
    field_name          VARCHAR(100)  NOT NULL,
    field_value         TEXT,
    source_url          VARCHAR(1000) NOT NULL,
    source_type         VARCHAR(50)   NOT NULL DEFAULT 'unknown',
    source_tier         INTEGER       NOT NULL DEFAULT 0 CHECK (source_tier BETWEEN 0 AND 5),
    evidence_text       TEXT,
    page_number         INTEGER,
    checked_at          DATE          NOT NULL DEFAULT CURRENT_DATE,
    published_at        DATE,
    freshness_status    VARCHAR(20)   DEFAULT 'unknown', -- fresh|recent|stale|unknown
    verification_status VARCHAR(20)   DEFAULT 'unverified',
    confidence_score    FLOAT         CHECK (confidence_score BETWEEN 0 AND 1),
    notes               TEXT,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ── Source Conflicts ──────────────────────────────────────────────────────
CREATE TABLE source_conflicts (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID          NOT NULL REFERENCES products(id),
    field_name          VARCHAR(100)  NOT NULL,
    source_a_url        VARCHAR(1000),
    source_a_value      TEXT,
    source_a_tier       INTEGER,
    source_b_url        VARCHAR(1000),
    source_b_value      TEXT,
    source_b_tier       INTEGER,
    conflict_type       VARCHAR(50)   DEFAULT 'value_mismatch',
    resolution          VARCHAR(50)   DEFAULT 'unresolved',
    resolution_notes    TEXT,
    detected_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    resolved            BOOLEAN       NOT NULL DEFAULT FALSE,
    resolved_at         TIMESTAMPTZ,
    resolved_by         TEXT
);

-- ── Change History (rate/fee change detection) ────────────────────────────
CREATE TABLE change_history (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID          NOT NULL REFERENCES products(id),
    field_name          VARCHAR(100)  NOT NULL,
    previous_value      TEXT,
    new_value           TEXT,
    change_amount       TEXT,
    previous_source     VARCHAR(1000),
    new_source          VARCHAR(1000),
    detected_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ── Calculation Results ───────────────────────────────────────────────────
CREATE TABLE calculation_results (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID          NOT NULL REFERENCES products(id),
    country_code        VARCHAR(2)    NOT NULL,
    product_category    VARCHAR(50),
    principal           FLOAT         NOT NULL,
    currency            CHAR(3)       NOT NULL,
    tenure_months       INTEGER,
    annual_rate         FLOAT,
    -- Loan fields
    monthly_installment FLOAT,
    total_payment       FLOAT,
    total_interest      FLOAT,
    known_fees_total    FLOAT         DEFAULT 0,
    estimated_total_cost FLOAT,
    -- Deposit fields
    gross_return        FLOAT,
    net_return          FLOAT,
    maturity_value      FLOAT,
    withholding_tax     FLOAT,
    effective_annual_rate FLOAT,
    -- Metadata
    formula_used        VARCHAR(100),
    calculation_label   TEXT,
    calculated_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ── Research Runs ─────────────────────────────────────────────────────────
CREATE TABLE research_runs (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID,
    country_code        VARCHAR(2),
    user_query          TEXT          NOT NULL,
    intent_json         JSONB,
    state               VARCHAR(50)   NOT NULL DEFAULT 'RECEIVED',
    search_queries      TEXT[],
    sources_visited     TEXT[],
    sources_accepted    TEXT[],
    sources_rejected    JSONB         DEFAULT '{}',
    products_found      INTEGER       DEFAULT 0,
    fields_extracted    INTEGER       DEFAULT 0,
    conflicts_detected  INTEGER       DEFAULT 0,
    calculations        JSONB         DEFAULT '[]',
    ranking             JSONB         DEFAULT '[]',
    final_answer        TEXT,
    total_llm_cost_usd  FLOAT         DEFAULT 0,
    execution_ms        INTEGER,
    error_message       TEXT,
    state_transitions   JSONB         DEFAULT '[]',
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

-- ── User Queries ──────────────────────────────────────────────────────────
CREATE TABLE user_queries (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID,
    country_code        VARCHAR(2),
    query               TEXT          NOT NULL,
    intent_json         JSONB,
    research_run_id     UUID          REFERENCES research_runs(id),
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ══════════════════════════════════════════════════════════════════════════
-- SEED DATA — Countries
-- ══════════════════════════════════════════════════════════════════════════

INSERT INTO countries VALUES
    ('BD', 'Bangladesh',    'BDT', '৳',  'before', TRUE,  '2026-08-04', 'en', '{"en","bn"}', FALSE, '🇧🇩', NOW()),
    ('IN', 'India',         'INR', '₹',  'before', FALSE, NULL,         'en', '{"en","hi"}', FALSE, '🇮🇳', NOW()),
    ('PK', 'Pakistan',      'PKR', 'Rs', 'before', FALSE, NULL,         'en', '{"en","ur"}', FALSE, '🇵🇰', NOW()),
    ('NP', 'Nepal',         'NPR', 'Rs', 'before', FALSE, NULL,         'en', '{"en","ne"}', FALSE, '🇳🇵', NOW()),
    ('LK', 'Sri Lanka',     'LKR', 'Rs', 'before', FALSE, NULL,         'en', '{"en","si"}', FALSE, '🇱🇰', NOW()),
    ('MY', 'Malaysia',      'MYR', 'RM', 'before', FALSE, NULL,         'en', '{"en","ms"}', FALSE, '🇲🇾', NOW()),
    ('ID', 'Indonesia',     'IDR', 'Rp', 'before', FALSE, NULL,         'id', '{"en","id"}', FALSE, '🇮🇩', NOW()),
    ('PH', 'Philippines',   'PHP', '₱',  'before', FALSE, NULL,         'en', '{"en","tl"}', FALSE, '🇵🇭', NOW()),
    ('NG', 'Nigeria',       'NGN', '₦',  'before', FALSE, NULL,         'en', '{"en"}',      FALSE, '🇳🇬', NOW()),
    ('GH', 'Ghana',         'GHS', '₵',  'before', FALSE, NULL,         'en', '{"en"}',      FALSE, '🇬🇭', NOW()),
    ('ZA', 'South Africa',  'ZAR', 'R',  'before', FALSE, NULL,         'en', '{"en"}',      FALSE, '🇿🇦', NOW()),
    ('SA', 'Saudi Arabia',  'SAR', '﷼',  'after',  FALSE, NULL,         'ar', '{"ar","en"}', TRUE,  '🇸🇦', NOW()),
    ('AE', 'UAE',           'AED', 'د.إ','after',  FALSE, NULL,         'ar', '{"ar","en"}', TRUE,  '🇦🇪', NOW()),
    ('EG', 'Egypt',         'EGP', '£E', 'before', FALSE, NULL,         'ar', '{"ar","en"}', TRUE,  '🇪🇬', NOW()),
    ('TZ', 'Tanzania',      'TZS', 'TSh','before', FALSE, NULL,         'sw', '{"en","sw"}', FALSE, '🇹🇿', NOW());

-- ══════════════════════════════════════════════════════════════════════════
-- INDEXES
-- ══════════════════════════════════════════════════════════════════════════

CREATE INDEX idx_products_country ON products(country_code);
CREATE INDEX idx_products_institution ON products(institution_id);
CREATE INDEX idx_products_category ON products(category, subcategory);
CREATE INDEX idx_product_versions_product ON product_versions(product_id);
CREATE INDEX idx_product_versions_current ON product_versions(product_id) WHERE is_current = TRUE;
CREATE INDEX idx_evidence_product_version ON evidence_records(product_version_id);
CREATE INDEX idx_evidence_field ON evidence_records(field_name);
CREATE INDEX idx_conflicts_product ON source_conflicts(product_id);
CREATE INDEX idx_research_runs_session ON research_runs(session_id);
CREATE INDEX idx_research_runs_country ON research_runs(country_code);
CREATE INDEX idx_change_history_product ON change_history(product_id);
CREATE INDEX idx_change_history_detected ON change_history(detected_at);
