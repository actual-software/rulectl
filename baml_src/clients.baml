// Learn more about clients at https://docs.boundaryml.com/docs/snippets/clients/overview

client<llm> CustomGPT4o {
  provider openai
  options {
    model "gpt-4o"
    api_key env.OPENAI_API_KEY
  }
}

client<llm> CustomGPT4oMini {
  provider openai
  retry_policy Exponential
  options {
    model "gpt-4o-mini"
    api_key env.OPENAI_API_KEY
  }
}

client<llm> CustomSonnet {
  provider anthropic
  retry_policy RateLimitRetry
  options {
    model "claude-sonnet-4-20250514"
    api_key env.ANTHROPIC_API_KEY
  }
}


client<llm> CustomHaiku {
  provider anthropic
  retry_policy Constant
  options {
    model "claude-3-haiku-20240307"
    api_key env.ANTHROPIC_API_KEY
  }
}

// https://docs.boundaryml.com/docs/snippets/clients/round-robin
client<llm> CustomFast {
  provider round-robin
  options {
    // This will alternate between the two clients
    strategy [CustomGPT4oMini, CustomHaiku]
  }
}

// https://docs.boundaryml.com/docs/snippets/clients/fallback
client<llm> OpenaiFallback {
  provider fallback
  options {
    // This will try the clients in order until one succeeds
    strategy [CustomGPT4oMini, CustomGPT4oMini]
  }
}

// Rate limit aware fallback strategy - tries Sonnet first, falls back to cheaper models
client<llm> RateLimitAware {
  provider fallback
  options {
    // Try Sonnet first, then fall back to cheaper models if rate limited
    strategy [CustomSonnet, CustomHaiku, CustomGPT4oMini]
  }
}

// Ollama client for local AI models
client<llm> OllamaClient {
  provider openai-generic
  retry_policy OllamaRetry
  options {
    base_url env.OLLAMA_BASE_URL
    model env.OLLAMA_MODEL
    // No API key needed for local Ollama
  }
}

// Ollama with cloud fallback for reliability
client<llm> OllamaWithFallback {
  provider fallback
  options {
    // Try Ollama first, fall back to cloud if it fails
    strategy [OllamaClient, CustomSonnet, CustomHaiku]
  }
}

// Adaptive client that prefers local Ollama but falls back to cloud providers
client<llm> AdaptiveClient {
  provider fallback
  options {
    // Will prefer Ollama if available, otherwise use cloud
    strategy [OllamaClient, CustomSonnet]
  }
}

// https://docs.boundaryml.com/docs/snippets/clients/retry
retry_policy Constant {
  max_retries 3
  // Strategy is optional
  strategy {
    type constant_delay
    delay_ms 200
  }
}

retry_policy Exponential {
  max_retries 2
  // Strategy is optional
  strategy {
    type exponential_backoff
    delay_ms 300
    multiplier 1.5
    max_delay_ms 10000
  }
}

// Special retry policy for rate limiting with longer delays
retry_policy RateLimitRetry {
  max_retries 3
  strategy {
    type exponential_backoff
    delay_ms 1000  // Start with 1 second delay
    multiplier 2.0  // Double the delay each time
    max_delay_ms 60000  // Max 1 minute delay
  }
}

// Retry policy for Ollama - faster retries for local connections
retry_policy OllamaRetry {
  max_retries 2
  strategy {
    type constant_delay
    delay_ms 500  // Quick retry for local server
  }
}