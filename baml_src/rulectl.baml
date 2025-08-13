function Hi(name: string) -> string {
  client CustomGPT4o
  prompt #"
    Say hello to the world.
  "#
}

test HelloWorld {
  functions [Hi]
  args {
    name "World"
  }
}

function ReviewSkippedFiles(project_info: string, skipped_files: FileInfo[]) -> SkippedFilesAnalysis {
  client CustomSonnet
  prompt #"
    You are analyzing a software project to determine which configuration/non-source files might contain useful coding patterns or conventions.

    Project context: {{ project_info }}

    These files were skipped from analysis because they appear to be configuration files:
    {% for file in skipped_files %}
    File: {{ file.path }}
    Extension: {{ file.extension }}
    Content preview (first 500 chars):
    {{ file.content }}
    ---
    {% endfor %}

    Determine which of these files might contain useful coding patterns, conventions, or architectural decisions that would be valuable for generating cursor rules.

    Files worth analyzing typically contain:
    - Custom configuration patterns (like next.config.js with complex webpack config)
    - ESLint/Prettier configs that show style preferences
    - Build scripts with custom logic
    - Schema definitions or type definitions in JSON
    - Docker configs with specific patterns
    - Custom tooling configurations

    Files NOT worth analyzing:
    - Simple package.json dependency lists
    - Basic tsconfig.json files
    - Lock files (package-lock.json, yarn.lock)
    - Generated files
    - Simple key-value config files

    Return:
    {{ctx.output_format}}
  "#
}