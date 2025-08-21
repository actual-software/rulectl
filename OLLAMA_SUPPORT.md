# Ollama Support for Local AI Models

This document describes how to use Rulectl with local AI models through Ollama, providing a cost-effective and privacy-focused alternative to cloud-based AI providers.

## Overview

Rulectl now supports running analysis with local AI models hosted on Ollama. This enables:
- **Cost Savings**: No API costs for cloud providers
- **Privacy**: Code analysis stays on your machine
- **Offline Capability**: Works without internet connection
- **Model Choice**: Use any Ollama-supported model
- **Performance**: Potentially faster response times for local models

## Prerequisites

### Install Ollama

1. **Download Ollama**: Visit [ollama.com](https://ollama.com) and download for your platform
2. **Install**: Follow platform-specific installation instructions
3. **Start Ollama**: Run `ollama serve` to start the server
4. **Download Models**: Install desired models (see [Model Selection](#model-selection))

### Verify Installation

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Should return JSON with available models
```

## Usage

### Basic Usage

**Default Behavior (No Ollama)**:
```bash
# Uses Anthropic Claude (cloud) by default
rulectl start
```

**Ollama Usage**:
Use the `--model` flag to specify a local Ollama model:

```bash
# Use llama3 model with default server
rulectl start --model llama3

# Specify custom server address
rulectl start --model qwen2 --server localhost:11434

# Use remote Ollama server
rulectl start --model mistral --server 192.168.1.100:11434
```

### Command Line Options

| Flag | Description | Default | Example |
|------|-------------|---------|---------|
| `--model` | Ollama model name | None (uses cloud) | `llama3`, `qwen2`, `mistral` |
| `--server` | Ollama server address | `localhost:11434` | `192.168.1.100:11434` |

### Model Selection

Popular models for code analysis:

| Model | Size | Description | Best For |
|-------|------|-------------|----------|
| `llama3` | 4.7GB | Meta's Llama 3 model | General code analysis |
| `qwen2` | 4.4GB | Alibaba's Qwen 2 model | Multilingual codebases |
| `mistral` | 4.1GB | Mistral 7B model | Fast analysis |
| `phi3` | 2.3GB | Microsoft Phi-3 model | Lightweight analysis |
| `gemma` | 5.0GB | Google Gemma model | Advanced reasoning |

Download models with:
```bash
ollama pull llama3
ollama pull qwen2
ollama pull mistral
```

## Architecture

### Client Selection

Rulectl uses an **AdaptiveClient** strategy with the following priority order:

#### When `--model` is specified:
1. **Ollama First**: Attempts to use specified local model
2. **Anthropic Fallback**: Falls back to Claude Sonnet if Ollama fails
3. **Additional Fallback**: Claude Haiku as final backup

#### When no `--model` is specified:
- **Default**: Uses Anthropic Claude Sonnet (cloud provider)
- **No Ollama**: Ollama is not attempted without explicit model specification

#### Client Priority Flow:
```
--model specified → OllamaClient → CustomSonnet (Claude) → CustomHaiku (Claude)
No --model       → CustomSonnet (Claude) directly
```

Benefits:
- **Transparent**: Same analysis quality regardless of provider
- **Reliable**: Multiple fallback layers ensure analysis completion
- **Cost-Aware**: Prefers free local models when available

### Integration Flow

```
CLI Flags → Environment Variables → BAML Configuration → Analysis
--model=llama3    OLLAMA_MODEL=llama3    AdaptiveClient       AnalyzeFiles()
--server=:11434   OLLAMA_BASE_URL=...    [Ollama→Cloud]       SynthesizeRules()
```

### Error Handling

Rulectl includes robust error handling:
- **Connection Testing**: Validates Ollama server before analysis
- **Model Validation**: Checks if requested model exists
- **Auto-Download**: Prompts for automatic model download if missing
- **Graceful Fallback**: Falls back to cloud providers if Ollama fails

## Configuration Examples

### Local Development

```bash
# Start Ollama
ollama serve

# Download and use llama3
ollama pull llama3
rulectl start --model llama3
```

### Remote Ollama Server

```bash
# Use Ollama running on another machine
rulectl start --model qwen2 --server 192.168.1.100:11434
```

### Custom Port

```bash
# Ollama running on custom port
ollama serve --port 8080
rulectl start --model mistral --server localhost:8080
```

### Docker Deployment

```bash
# Run Ollama in Docker
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Use with Rulectl
rulectl start --model llama3 --server localhost:11434
```

## Performance Considerations

### Model Size vs Performance

| Model Size | RAM Required | Analysis Speed | Quality |
|------------|--------------|----------------|---------|
| Small (2-4GB) | 8GB+ | Fast | Good |
| Medium (4-8GB) | 16GB+ | Moderate | Very Good |
| Large (8GB+) | 32GB+ | Slower | Excellent |

### Optimization Tips

1. **GPU Acceleration**: Use NVIDIA GPUs for faster inference
2. **Model Caching**: Keep frequently used models downloaded
3. **RAM**: Ensure adequate RAM for model + analysis
4. **SSD Storage**: Use fast storage for model files

## Troubleshooting

### Common Issues

#### Ollama Not Running
```
❌ Failed to connect to Ollama server at http://localhost:11434
💡 Make sure Ollama is running: 'ollama serve'
```
**Solution**: Start Ollama with `ollama serve`

#### Model Not Found
```
⚠️  Model 'llama3' not found on server
📦 Available models: mistral, qwen2
Continue anyway? (Ollama may download the model automatically)
```
**Solution**: Download model with `ollama pull llama3` or let Ollama download automatically

#### Connection Timeout
```
❌ Connection timeout to Ollama server at http://localhost:11434
💡 Make sure Ollama is running and accessible
```
**Solution**: Check Ollama status, firewall settings, or server address

#### Out of Memory
```
❌ Model loading failed: insufficient memory
```
**Solution**: Use smaller model or increase available RAM

### Debug Mode

Use verbose mode for detailed debugging:
```bash
rulectl start --model llama3 --verbose
```

This shows:
- Connection testing details
- Available models
- Model validation results
- Fallback behavior

### Manual Testing

Test Ollama connectivity manually:
```bash
# List available models
curl http://localhost:11434/api/tags

# Test chat completion
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Security Considerations

### Local Processing Benefits
- **No Data Transmission**: Code stays on your machine
- **No API Keys**: No cloud provider credentials needed
- **Network Independence**: Works offline

### Access Control
- Ollama runs locally with user permissions
- No external network requirements
- Standard file system security applies

## Comparison: Cloud vs Local

| Aspect | Cloud Providers (Default) | Local Ollama |
|--------|---------------------------|--------------|
| **Default** | ✅ Anthropic Claude | Requires `--model` flag |
| **Cost** | Pay per token | Free after setup |
| **Privacy** | Data sent to cloud | Data stays local |
| **Speed** | Network dependent | Hardware dependent |
| **Models** | Latest/proprietary | Open source |
| **Setup** | API keys only | Install + download |
| **Reliability** | Service dependent | Hardware dependent |

## Best Practices

1. **Model Selection**: Choose models appropriate for your hardware
2. **Regular Updates**: Keep Ollama and models updated
3. **Monitoring**: Monitor resource usage during analysis
4. **Backup Strategy**: Consider cloud fallback for critical workflows
5. **Testing**: Test locally before production analysis

## Examples

### Complete Workflow

```bash
# 1. Install and start Ollama
ollama serve

# 2. Download preferred model
ollama pull llama3

# 3. Verify model availability
ollama list

# 4. Run analysis with local model
cd /path/to/your/project
rulectl start --model llama3 --verbose

# 5. Enjoy cost-free, private analysis!
```

### Multi-Model Setup

```bash
# Download multiple models for different use cases
ollama pull llama3      # General purpose
ollama pull qwen2       # Multilingual
ollama pull phi3        # Lightweight

# Use different models for different projects
rulectl start --model llama3   # For large projects
rulectl start --model phi3     # For quick analysis
```

### Integration with CI/CD

```yaml
# GitHub Actions example
- name: Setup Ollama
  run: |
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve &
    ollama pull llama3

- name: Run Rulectl Analysis
  run: |
    rulectl start --model llama3 --force
```

## Limitations

- **Model Size**: Large models require significant RAM
- **First Run**: Initial model download can be slow
- **Hardware Dependent**: Performance varies with hardware
- **Model Updates**: Manual model management required

## Future Enhancements

- **Automatic Model Selection**: Choose optimal model based on project size
- **Performance Monitoring**: Built-in performance metrics
- **Model Recommendations**: Suggest best models for specific codebases
- **Distributed Ollama**: Support for Ollama clusters