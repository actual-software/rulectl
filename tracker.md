# Rulectl Issue Tracker

It is paramount above all that this markdown file `tracker.md` is not commit to the repository, but also not added to the .gitignore. You just have to be careful.

> Status: Active Development | Last Updated: 2025-08-07

## 🤖 AI Development Instructions

**For AI coding agents (Claude Code, etc.):**

Each issue in this tracker should be handled as follows:

1. **Branch Strategy**: Create individual branches for each issue using prefixes:
   - `bug/api-credit-validation` 
   - `feat/batch-rule-acceptance`
   - `doc/setup-guide-completeness`

2. **Development Process**:
   - Start by analyzing developer needs and user intent for the specific issue
   - Ask clarifying questions about requirements, scope, and expected behavior
   - **For well-defined issues with clear specs**: Consider direct implementation
   - **For complex/ambiguous issues**: Provide example format/output after questions are answered
   - Generate a detailed implementation plan based on feedback **when needed**
   - Wait for user approval of the plan before proceeding **for complex changes**
   - Break approved plan into small, manageable development chunks
   - Track progress on individual tasks using available memory systems
   - Develop incrementally with regular progress updates
   - Track all knowledge as you go in Serena MCP memory
   - Use TodoWrite tool proactively to track multi-step tasks and demonstrate progress
   - For well-defined issues: Consider implementing directly if requirements are clear
   - Always explore codebase thoroughly before implementing (use find_symbol, search_for_pattern)
   - Test syntax and basic functionality after each major change

3. **Completion Requirements**:
   - Commit files in logical, well-structured commits with detailed messages
   - Open pull request with descriptive, professional title
   - Use academic tone suitable for developer audience
   - Avoid marketing language, emojis, or promotional content
   - Focus on technical implementation and problem-solving

4. **Isolation Policy**: Each issue must remain completely isolated from other changes. Do not combine multiple issues in a single branch or PR.

5. **Technical Excellence Guidelines**:
   - Implement surgical, focused changes that preserve existing functionality
   - Use semantic analysis tools to understand code structure before editing
   - Test imports, syntax, and basic CLI functionality after implementation
   - For sorting/ordering features: implement just before user presentation
   - Maintain backward compatibility unless explicitly requested otherwise
   - Use TodoWrite to track progress on complex multi-step implementations

6. **Quality Assurance Flow**:
   - Syntax validation: `python -m py_compile <modified_files>`
   - Import testing: `python -c "import module; print('✅ Import successful')"`
   - Basic functionality: Test CLI help or basic commands
   - Integration testing: Run relevant test suites if available

**Example Branch/PR Workflow**:
```
git checkout -b bug/api-credit-validation
# ... development work ...
git commit -m "Add early API credit validation to prevent workflow interruption"
gh pr create --title "Fix API credit validation timing to occur before lengthy operations"
```

---

## ULTRA HIGH PRIORITY CHANGE

We've renamed the repository from rules_engine to rulectl -- The whole repository, all it's references, examles, and documentation should be updated to `rulectl`

---

## ⭐ Medium Priority Issues

### 🐛 bug: Progress Timer Update Frequency
**Priority**: Medium | **Status**: Open | **Complexity**: Low

**Problem**: Predicted time remaining only updates when new files are started, not continuously

**Current Behavior**: Timer appears frozen between file processing
**Expected Behavior**: Timer should update every 1-2 seconds to show realistic progress
**Technical Details**: Need background timer thread for UI updates
**User Impact**: Poor user experience during long analysis runs

---

### 🐛 bug: File Preview Character Truncation
**Priority**: Medium | **Status**: Open | **Complexity**: Medium

**Problem**: Skipped file content previews cut off the final character(s) in file snippets

**Evidence Examples**:
- "python-versio" instead of "python-version"
- "--create-file-if-not-exist=tr" instead of "--create-file-if-not-exist=true"
- "runs-on: ubuntu-lat" instead of "runs-on: ubuntu-latest"

**Impact**: Degraded user experience during file analysis review
**Location**: File content preview generation logic (likely string slicing issue)

**Reproduction**: Visible in skipped file previews during analysis phase

---

### ✨ feat: Claude Code Rules Output Format
**Priority**: Medium | **Status**: Open | **Complexity**: Medium

**Problem**: Rules only export to Cursor format, limiting IDE compatibility

**Requirements**:
- Add Claude Code rules format support
- Maintain existing Cursor format
- Allow format selection during export
- Ensure feature parity between formats

**Implementation**: Add `--output-format` flag with options: `cursor`, `claude`, `both`

---

## 💡 Low Priority Issues

### 📚 doc: Setup Guide Completeness
**Priority**: Low | **Status**: Open | **Complexity**: Low

**Missing Documentation**:
- Virtual environment setup instructions
- requirements.txt installation step  
- Working directory requirements
- Complete build process walkthrough

**Current Setup Issues Users Face**:
1. No mention of `python -m venv venv` step
2. Missing `pip install -r requirements.txt`
3. Directory context not specified (must be in repo root)
4. Build process unclear

**Required Steps Currently Undocumented**:
```bash
# Missing from README:
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cd /path/to/repo/root
python build.py
```

---

### 📚 doc: Binary Distribution Guide
**Priority**: Low | **Status**: Open | **Complexity**: Low

**Missing Coverage**:
- Post-build binary installation options
- PATH modification strategies  
- Symlink vs copy recommendations
- Permission considerations

**User Needs**:
- Permanent installation guidance
- Cross-platform installation notes
- Uninstallation procedures

**Current User Workarounds**:
```bash
# User-discovered solutions not documented:
ln -s /path/to/repo/dist/rulectl /usr/local/bin/
# OR
cp /path/to/repo/dist/rulectl /usr/local/bin/
```

---

### ✨ feature: Homebrew Package Distribution
**Priority**: Low | **Status**: Open | **Complexity**: High  

**Prerequisites**:
- Multi-platform binary builds (macOS Intel/ARM, Linux x64/ARM)
- Automated CI/CD pipeline
- Semantic versioning system
- GitHub Releases automation
- Homebrew formula creation
- Package signing/verification

**Benefits**: Industry-standard installation method for macOS/Linux users

**Installation Target**:
```bash
brew install actualai/tap/rulectl
rulectl --version
```

---