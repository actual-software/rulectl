// Core types for repository analysis
class FileInfo {
    path string
    content string
    extension string
}

class CodePattern {
    name string
    description string
    confidence float
    examples string[]
}

class RuleCandidate {
    name string
    description string
    pattern string
    confidence float
    examples string[]
    suggested_category string  // The category file this rule should go in (e.g. "style", "build", etc)
}

// New types for static analysis
class StaticAnalysisRule {
    slug string  // lowercase-kebab-case ≤ 5 words
    description string  // 1-sentence summary (≤ 120 chars)
    scope_glob string  // default to the file's dir if unsure
    bullets string[]  // 1-5 actionable bullets, each ≤ 120 chars
    evidence_lines int[]  // array of line numbers that justify the rule
}

class StaticAnalysisResult {
    file string  // relative path
    rules StaticAnalysisRule[]  // max 5 candidates
}

class BatchAnalysis {
    files FileInfo[]
    patterns CodePattern[]
    suggested_rules RuleCandidate[]
}

// Static analysis function for single file inspection
function AnalyzeFileForConventions(file: FileInfo) -> StaticAnalysisResult {
    client AdaptiveClient
    prompt #"
    You are a static-analysis assistant.
    Your job is to inspect ONE source file and emit **JSON** describing *project-specific* conventions
    that could become Cursor .mdc rules.
    DO NOT output explanations, markdown, or code – JSON only.

    Guidelines
    1. Capture only **non-obvious, repo-specific guidance** (e.g. "use Tailwind + shadcn/ui"),
       not generic style advice.
    2. Each candidate must include:
       • slug    -  lowercase-kebab-case ≤ 5 words  
       • description - 1-sentence summary (≤ 120 chars)  
       • scope_glob  -  default to the file's dir (`src/components/**/*`) if unsure  
       • bullets     -  1-5 actionable bullets, each ≤ 120 chars  
       • evidence_lines  -  array of line numbers (no code) that justify the rule
    3. Max **5** candidates. Return `"rules": []` when no valid conventions exist.
    4. Output must fit in ≤ 2 000 tokens.

    {{ ctx.output_format }}

    File to analyze: {{ file.path }}
    
    <--- BEGIN FILE CONTENT (truncated to ≤ 1 500 lines with 1-based numbering) --->
    {{ file.content }}
    <--- END FILE CONTENT --->
    "#
}

// Updated synthesis function for static analysis results
function SynthesizeRules(analyses: StaticAnalysisResult[]) -> RuleCandidate[] {
    client AdaptiveClient
    prompt #"
    You are an expert at creating Cursor rules based on static analysis results.
    Review the following file analyses and synthesize them into a cohesive set of rules.
    Focus on patterns that appear across multiple files and have high confidence based on evidence.

    For each synthesized rule, recommend a category file it should be placed in. Categories should be high-level groupings like:
    - style (coding style and formatting)
    - build (build system and dependencies)
    - security (security practices)
    - testing (testing practices)
    - performance (performance optimizations)
    - architecture (code organization)
    etc.

    The category should reflect the primary purpose of the rule and will determine which .mdc file it goes in.

    Look for:
    1. Rules that appear across multiple files with similar patterns
    2. Consistent conventions that could be automated
    3. Project-specific patterns worth codifying

    {{ ctx.output_format }}

    Static Analysis Results:
    {% for analysis in analyses %}
    --- File: {{ analysis.file }} ---
    Rules found: {{ analysis.rules|length }}
    {% for rule in analysis.rules %}
    - {{ rule.slug }}: {{ rule.description }}
      Scope: {{ rule.scope_glob }}
      Evidence lines: {{ rule.evidence_lines }}
      Bullets: {{ rule.bullets }}
    {% endfor %}

    {% endfor %}
    "#
}

// Main analysis functions (kept for backward compatibility)
function AnalyzeCodeBatch(files: FileInfo[]) -> BatchAnalysis {
    client AdaptiveClient
    prompt #"
    You are an expert code analyzer focusing on identifying patterns and generating Cursor rules.
    Analyze the following code files and identify:
    1. Common coding patterns
    2. Style conventions
    3. Potential Cursor rules that could be automated

    For each pattern, suggest a category for the rule. Categories should be high-level groupings like:
    - style (coding style and formatting)
    - build (build system and dependencies)
    - security (security practices)
    - testing (testing practices)
    - performance (performance optimizations)
    - architecture (code organization)
    - etc.

    {{ ctx.output_format }}

    Files to analyze:
    {% for file in files %}
    --- {{ file.path }} ---
    {{ file.content }}

    {% endfor %}
    "#
}

// Optional: Specialized analyzers for different file types
function AnalyzeTypeScript(file: FileInfo) -> CodePattern[] {
    client AdaptiveClient
    prompt #"
    You are an expert TypeScript analyzer. Analyze this TypeScript file and identify:
    1. TypeScript-specific patterns
    2. Type usage patterns
    3. React patterns (if applicable)
    4. Import/export patterns

    {{ ctx.output_format }}

    File: {{ file.path }}
    Content:
    {{ file.content }}
    "#
}

function AnalyzePython(file: FileInfo) -> CodePattern[] {
    client AdaptiveClient
    prompt #"
    You are an expert Python analyzer. Analyze this Python file and identify:
    1. Python-specific idioms
    2. Type hint usage
    3. Import patterns
    4. Common Python conventions

    {{ ctx.output_format }}

    File: {{ file.path }}
    Content:
    {{ file.content }}
    "#
}

// Rule auditing and improvement function
function AuditMergedRule(
    cluster_key: string,
    merged_rule: StaticAnalysisRule,
    original_rules: StaticAnalysisRule[]
) -> StaticAnalysisRule {
    client AdaptiveClient
    prompt #"
    You are a code rule auditor. Your job is to clean up a merged coding rule that was created 
    by clustering similar rules together. The merge may have created nonsensical combinations.

    TASK: Audit and improve the merged rule by:
    1. Removing bullets that don't fit the cluster theme
    2. Keeping only coherent, related bullets (max 5)
    3. Improving the description to match the actual bullets
    4. Ensuring the scope_glob makes sense for the rule content
    5. Making sure the slug is appropriate

    CLUSTER THEME: {{ cluster_key }}
    
    MERGED RULE TO AUDIT:
    - Slug: {{ merged_rule.slug }}
    - Description: {{ merged_rule.description }}
    - Scope: {{ merged_rule.scope_glob }}
    - Bullets: {{ merged_rule.bullets }}
    
    ORIGINAL RULES THAT WERE MERGED:
    {% for rule in original_rules %}
    Rule {{ loop.index }}:
    - From file: (evidence lines {{ rule.evidence_lines }})
    - Slug: {{ rule.slug }}
    - Description: {{ rule.description }}
    - Bullets: {{ rule.bullets }}
    
    {% endfor %}

    OUTPUT REQUIREMENTS:
    - Return a clean, coherent rule with bullets that actually relate to each other
    - If the merge doesn't make sense, focus on the most represented theme
    - Bullets should be actionable and specific to the cluster theme
    - Description should accurately reflect what the bullets actually do
    - Scope should target the right file types/directories for this rule
    - Keep slug concise and descriptive (kebab-case, ≤5 words)

    {{ ctx.output_format }}
    "#
}

// Rule categorization function
class RuleCategory {
    category_name string  // Concise name like "architecture", "testing", etc
    description string    // Brief description of what this category covers
    rules StaticAnalysisRule[]  // Rules that belong in this category
}

function CategorizeAcceptedRules(accepted_rules: StaticAnalysisRule[]) -> RuleCategory[] {
    client AdaptiveClient
    prompt #"
    You are a code organization expert. Your job is to categorize accepted coding rules 
    into logical, concise categories suitable for .mdc filenames.

    TASK: Group the provided rules into 3-7 logical categories with:
    1. Concise category names (1-2 words, lowercase, no hyphens)
    2. Clear descriptions of what each category covers
    3. Logical grouping of related rules

    GOOD CATEGORY NAMES:
    - architecture (code organization, patterns, structure)
    - testing (test patterns, mocking, fixtures)
    - configuration (env vars, setup, config files)
    - security (API keys, credentials, validation)
    - build (compilation, packaging, deployment)
    - style (naming, formatting, conventions)
    - performance (optimization, efficiency)
    - tooling (CLI patterns, utilities, scripts)

    AVOID:
    - Long names, hyphens, or technical jargon
    - Too many categories (keep it manageable)
    - Overly specific categories (group related concepts)

    RULES TO CATEGORIZE:
    {% for rule in accepted_rules %}
    Rule {{ loop.index }}:
    - Slug: {{ rule.slug }}
    - Description: {{ rule.description }}
    - Scope: {{ rule.scope_glob }}
    - Bullets: {{ rule.bullets }}
    
    {% endfor %}

    OUTPUT: Return categories that make logical sense for organizing these specific rules.
    Each rule should appear in exactly one category.

    {{ ctx.output_format }}
    "#
}

test TestName {
  functions [AnalyzeFileForConventions]
  args {
    file {
      path "test.py"
      content "print('Hello, world!')"
      extension ".py"
    }
  }
}

function TestHelloWorld(name: string) -> string {
  client AdaptiveClient
  prompt #"
  Say hello to the world.
  "#
}

test TestHelloWorld {
  functions [TestHelloWorld]
  args {
    name "World"
  }
}

// Types for reviewing skipped files
class SkippedFileReview {
    file_path string
    should_analyze bool
    reasoning string
    potential_patterns string[]
}

class SkippedFilesAnalysis {
    files_to_analyze string[]
    reasoning string
}