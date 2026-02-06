/*
Quality Control Tables Migration
Adds tables to track paper validation, essay quality metrics, and quality control results
*/

-- Table for paper validation results
CREATE TABLE PaperValidation (
    validation_id INT IDENTITY(1,1) PRIMARY KEY,
    paper_id INT,
    title NVARCHAR(MAX),
    authors NVARCHAR(MAX),
    doi NVARCHAR(100),
    is_valid BIT DEFAULT 1,
    is_retracted BIT DEFAULT 0,
    validation_level NVARCHAR(20),  -- 'basic', 'doi', 'venue', 'full'
    venue_quality_score DECIMAL(3,1),
    citation_count INT DEFAULT 0,
    published_year INT,
    validation_metadata NVARCHAR(MAX),  -- JSON storing detailed validation data
    validated_at DATETIME2 DEFAULT GETDATE(),
    created_at DATETIME2 DEFAULT GETDATE()
);

-- Create index on DOI for faster lookups
CREATE INDEX idx_paper_validation_doi ON PaperValidation(doi);
CREATE INDEX idx_paper_validation_is_valid ON PaperValidation(is_valid);

-- Table for essay quality metrics
CREATE TABLE EssayQualityMetrics (
    metric_id INT IDENTITY(1,1) PRIMARY KEY,
    session_id NVARCHAR(50),
    essay_id INT,
    overall_score DECIMAL(3,1),
    citation_density_score DECIMAL(3,1),
    source_diversity_score DECIMAL(3,1),
    academic_language_score DECIMAL(3,1),
    structural_coherence_score DECIMAL(3,1),
    evidence_based_claims_score DECIMAL(3,1),
    citation_accuracy_score DECIMAL(3,1),
    word_count INT,
    citation_count INT,
    assessment_level NVARCHAR(50),  -- 'excellent', 'good', 'acceptable_with_review', 'rejected'
    quality_issues NVARCHAR(MAX),  -- JSON array of issues
    regeneration_attempts INT DEFAULT 0,
    assessed_at DATETIME2 DEFAULT GETDATE(),
    created_at DATETIME2 DEFAULT GETDATE()
);

CREATE INDEX idx_essay_quality_session ON EssayQualityMetrics(session_id);
CREATE INDEX idx_essay_quality_overall_score ON EssayQualityMetrics(overall_score);

-- Table for citation verification results
CREATE TABLE CitationVerification (
    verification_id INT IDENTITY(1,1) PRIMARY KEY,
    session_id NVARCHAR(50),
    essay_id INT,
    total_citations INT,
    total_references INT,
    orphan_citations INT,
    unused_references INT,
    citation_mismatches INT,
    success_rate DECIMAL(3,2),
    is_valid BIT,
    verification_details NVARCHAR(MAX),  -- JSON with details
    verified_at DATETIME2 DEFAULT GETDATE(),
    created_at DATETIME2 DEFAULT GETDATE()
);

CREATE INDEX idx_citation_verification_session ON CitationVerification(session_id);
CREATE INDEX idx_citation_verification_is_valid ON CitationVerification(is_valid);

-- Table for fact-checking results
CREATE TABLE FactCheckingResults (
    fact_check_id INT IDENTITY(1,1) PRIMARY KEY,
    session_id NVARCHAR(50),
    essay_id INT,
    claims_verified INT,
    claims_supported INT,
    supported_percentage DECIMAL(3,2),
    is_valid BIT,
    verification_details NVARCHAR(MAX),  -- JSON with claim details
    checked_at DATETIME2 DEFAULT GETDATE(),
    created_at DATETIME2 DEFAULT GETDATE()
);

CREATE INDEX idx_fact_checking_session ON FactCheckingResults(session_id);
CREATE INDEX idx_fact_checking_is_valid ON FactCheckingResults(is_valid);

-- Table to track overall quality control results per session
CREATE TABLE QualityControlSummary (
    summary_id INT IDENTITY(1,1) PRIMARY KEY,
    session_id NVARCHAR(50) UNIQUE,
    papers_fetched INT,
    papers_validated INT,
    source_sufficiency_passed BIT,
    quality_score DECIMAL(3,1),
    citation_verification_passed BIT,
    fact_checking_passed BIT,
    overall_quality_passed BIT,
    essay_generated BIT DEFAULT 0,
    regeneration_attempts INT DEFAULT 0,
    quality_assessment_duration_ms INT,
    summary_metadata NVARCHAR(MAX),  -- JSON with full summary
    completed_at DATETIME2,
    created_at DATETIME2 DEFAULT GETDATE()
);

CREATE INDEX idx_quality_control_session ON QualityControlSummary(session_id);
CREATE INDEX idx_quality_control_overall_passed ON QualityControlSummary(overall_quality_passed);

-- Table for validation cache (to avoid re-validating same papers)
CREATE TABLE PaperValidationCache (
    cache_id INT IDENTITY(1,1) PRIMARY KEY,
    paper_hash NVARCHAR(64),  -- SHA256 of paper DOI/title
    validation_result NVARCHAR(MAX),  -- JSON
    cached_at DATETIME2 DEFAULT GETDATE(),
    expires_at DATETIME2,  -- 24 hours from cached_at
    CONSTRAINT uq_paper_hash UNIQUE(paper_hash)
);

CREATE INDEX idx_validation_cache_expires ON PaperValidationCache(expires_at);
