# YAML Configuration Guide

This guide explains how to configure agents and pipelines using YAML files. The YAML-based configuration system makes it easy to modify agent behavior, add new agents, and change pipeline flow without touching Python code.

## Table of Contents

1. [Overview](#overview)
2. [Agent Configuration](#agent-configuration)
3. [Pipeline Configuration](#pipeline-configuration)
4. [Agent Types](#agent-types)
5. [HITL Configuration](#hitl-configuration)
6. [Examples](#examples)

---

## Overview

The configuration system consists of two types of YAML files:

1. **Agent YAML files** (`backend/agents/*.yaml`) - Define individual agent behavior
2. **Pipeline YAML file** (`backend/config/pipeline.yaml`) - Define agent execution sequence

### File Structure

```
backend/
├── agents/
│   ├── planner.yaml
│   ├── art_director.yaml
│   ├── dop.yaml
│   ├── generator.yaml
│   └── critic.yaml
└── config/
    └── pipeline.yaml
```

---

## Agent Configuration

Each agent is defined in a YAML file with the following structure:

### Basic Structure

```yaml
# Agent metadata
name: agent_name                    # Internal name (must match filename)
display_name: Agent Display Name    # Human-readable name
description: What this agent does

# Model configuration
model:
  provider: gemini                  # Model provider (gemini, registry)
  name: gemini-3.1-pro-preview      # Model name
  temperature: 0.7                  # Generation temperature (0.0-1.0)
  max_tokens: 2048                  # Max output tokens

# System instruction
instruction: |
  Multi-line instruction for the agent.
  Tells the agent how to behave and what to output.

# Inputs and outputs
inputs:
  - name: input_name
    type: string
    source: context.field_name
    description: What this input is

outputs:
  - name: output_name
    type: string
    target: context.field_name
    description: What this output is

# HITL configuration (optional)
hitl:
  enabled: true
  # ... (see HITL section)

# Agent type
type: llm_agent                     # llm_agent, generator_agent, critic_agent
```

### Field Reference

#### Name Fields

- **`name`** (required): Internal agent name. Must match the YAML filename (without .yaml)
- **`display_name`** (optional): Human-readable name shown in UI. Defaults to title-cased `name`
- **`description`** (optional): Brief description of the agent's purpose

#### Model Configuration

- **`model.provider`**: Model provider
  - `gemini` - Use Google Gemini directly
  - `registry` - Use backend from registry (for generator/critic agents)
- **`model.name`**: Specific model name (e.g., `gemini-3.1-pro-preview`)
- **`model.temperature`**: Sampling temperature (0.0 = deterministic, 1.0 = creative)
- **`model.max_tokens`**: Maximum tokens in output
- **`model.backend_key`**: Environment variable for registry-based models (e.g., `GENERATOR_BACKEND`)

#### Instruction

- **`instruction`**: Multi-line system prompt that defines agent behavior
  - Use `|` for multi-line strings in YAML
  - Be specific about input format and expected output
  - Include examples if helpful

#### Inputs

Each input defines where the agent reads data from:

```yaml
inputs:
  - name: input_name              # Internal name
    type: string                  # Data type (string, PIL.Image, dict, etc.)
    source: context.field_name    # Where to read from PipelineContext
    fallback: context.other_field # Optional: Use if source is None
    optional: true                # Optional: Allow None values
    default: "default value"      # Optional: Default if None
    description: What this is     # Human-readable description
```

**Source syntax:**
- `context.field_name` - Read from PipelineContext attribute
- Nested fields: `context.metadata.key_name`

#### Outputs

Each output defines where the agent writes results:

```yaml
outputs:
  - name: output_name            # Internal name
    type: string                 # Data type
    target: context.field_name   # Where to write in PipelineContext
    append: false                # Optional: Append to list instead of replace
    description: What this is    # Human-readable description
```

**Target syntax:**
- `context.field_name` - Write to PipelineContext attribute
- Nested fields: `context.metadata.key_name`
- If `append: true` and target is a list, appends instead of replacing

#### Agent Type

- **`type`**: Defines how the agent executes
  - `llm_agent` - Calls LLM with instruction + inputs
  - `generator_agent` - Generates images using backend
  - `critic_agent` - Critiques images using backend

---

## Pipeline Configuration

The pipeline configuration defines the execution sequence of agents.

### File: `config/pipeline.yaml`

```yaml
# Main pipeline configuration
pipeline:
  name: image_generation_pipeline
  description: Full pipeline from prompt to critique with HITL gates

  # Agent execution sequence
  agents:
    - planner
    - art_director
    - dop
    - generator
    - critic

  # Pipeline-wide settings
  settings:
    enable_hitl: true            # Enable Human-in-the-Loop gates

    context_defaults:
      aspect_ratio: "1:1"
      metadata: {}

    error_handling:
      continue_on_error: false
      log_errors: true

    timeout_seconds: 300         # Max time per agent

# Alternative pipeline configurations
pipelines:
  quick:
    agents:
      - planner
      - generator
      - critic
    settings:
      enable_hitl: false

  minimal:
    agents:
      - generator
      - critic
    settings:
      enable_hitl: false

# Active pipeline
active_pipeline: pipeline        # Name of pipeline to use
```

### Switching Pipelines

To use a different pipeline, change the `active_pipeline` value:

```yaml
active_pipeline: quick  # Use the "quick" pipeline instead
```

Or set via environment variable:
```bash
export PIPELINE_MODE=quick
```

---

## Agent Types

### 1. LLM Agent

LLM agents call a language model with instructions and inputs.

```yaml
name: planner
type: llm_agent

model:
  provider: gemini
  name: gemini-3.1-pro-preview
  temperature: 0.7

instruction: |
  You are a creative planner...

inputs:
  - name: original_prompt
    type: string
    source: context.original_prompt

outputs:
  - name: enriched_prompt
    type: string
    target: context.enriched_prompt
```

**How it works:**
1. Gathers input values from PipelineContext
2. Builds prompt: `instruction + "\n\n" + formatted_inputs`
3. Calls LLM model
4. Writes output to PipelineContext

### 2. Generator Agent

Generator agents create images using the registered image generation backend.

```yaml
name: generator
type: generator_agent

model:
  provider: registry
  backend_key: GENERATOR_BACKEND

inputs:
  - name: enriched_prompt
    type: string
    source: context.enriched_prompt
  - name: aspect_ratio
    type: string
    source: context.aspect_ratio

outputs:
  - name: image
    type: PIL.Image
    target: context.image

behaviors:
  combine_prompts: true          # Combine multiple prompt fields
  separator: "\n\n"
  save_output: true
  output_path: outputs/00_initial.png
```

**Special behaviors:**
- `combine_prompts: true` - Combines `enriched_prompt`, `style_brief`, `shot_brief`
- `save_output: true` - Saves generated image to file

### 3. Critic Agent

Critic agents analyze images and suggest improvements.

```yaml
name: critic
type: critic_agent

model:
  provider: registry
  backend_key: CRITIC_BACKEND

inputs:
  - name: image
    type: PIL.Image
    source: context.image
  - name: original_prompt
    type: string
    source: context.original_prompt

outputs:
  - name: critique
    type: dict
    target: context.critiques
    append: true                 # Append to list of critiques

behaviors:
  save_annotated: true
  annotated_path: outputs/01_annotated.png
```

---

## HITL Configuration

Human-in-the-Loop (HITL) gates allow users to review and approve agent outputs before continuing.

### HITL Structure

```yaml
hitl:
  enabled: true                                    # Enable HITL for this agent
  review_stage: awaiting_planner_review            # State name for review
  output_label: Enriched prompt                    # Label shown to user

  # Messages
  approval_message: Approved enriched prompt.
  thinking_message: Planning and expanding prompt...
  thinking_revise_message: Revising based on feedback...

  # Review prompt and options
  review_prompt: Does this enriched prompt look good?
  options:
    - label: "✓ Approve - Continue to style"
      value: approve
    - label: "✎ Give feedback"
      value: feedback
    - label: "✕ Start over"
      value: reject

  # Next agent configuration
  next_agent: art_director                         # Agent to run after approval
  next_stage: awaiting_art_director_review         # Next review state
  next_label: Continue to style                    # Label for next step

  # Feedback configuration
  feedback_target: original_prompt                 # Where to append user feedback
```

### HITL Field Reference

- **`enabled`**: Whether to show review gate for this agent
- **`review_stage`**: State name (must match pattern `awaiting_{agent}_review`)
- **`output_label`**: Human-readable label for the output
- **`approval_message`**: Message shown when user approves
- **`thinking_message`**: Message shown while agent is running (initial)
- **`thinking_revise_message`**: Message shown when agent re-runs with feedback
- **`review_prompt`**: Question shown to user
- **`options`**: List of buttons shown to user
  - `label`: Button text
  - `value`: Internal value (`approve`, `feedback`, `reject`)
- **`next_agent`**: Name of agent to run after approval
- **`next_stage`**: Next review state to enter
- **`next_label`**: Label for next step button
- **`feedback_target`**: Where to append user feedback in PipelineContext

---

## Examples

### Example 1: Simple LLM Agent

Create a new agent that generates titles for images:

```yaml
# agents/title_generator.yaml
name: title_generator
display_name: Title Generator
description: Generates catchy titles for images

model:
  provider: gemini
  name: gemini-3.1-pro-preview
  temperature: 0.9

instruction: |
  You are a creative copywriter. Generate a catchy, memorable title for an image based on the prompt.

  The title should be:
  - Short (3-7 words)
  - Engaging and memorable
  - Relevant to the image content

  Return ONLY the title, no explanation.

inputs:
  - name: enriched_prompt
    type: string
    source: context.enriched_prompt
    fallback: context.original_prompt

outputs:
  - name: image_title
    type: string
    target: context.metadata.image_title

hitl:
  enabled: true
  review_stage: awaiting_title_review
  output_label: Image title
  approval_message: Approved title.
  thinking_message: Generating title...
  thinking_revise_message: Revising title based on feedback...
  review_prompt: Do you like this title?
  options:
    - label: "✓ Approve"
      value: approve
    - label: "✎ Suggest changes"
      value: feedback
  next_agent: art_director
  next_stage: awaiting_art_director_review
  next_label: Continue
  feedback_target: enriched_prompt

type: llm_agent
```

Add to pipeline:

```yaml
# config/pipeline.yaml
pipeline:
  agents:
    - planner
    - title_generator  # New agent
    - art_director
    - dop
    - generator
    - critic
```

### Example 2: Pipeline Without HITL

Create a fast pipeline without review gates:

```yaml
# config/pipeline.yaml
pipelines:
  fast:
    agents:
      - generator
      - critic
    settings:
      enable_hitl: false
      timeout_seconds: 60

active_pipeline: fast  # Use fast pipeline
```

### Example 3: Custom Agent with Multiple Inputs

```yaml
# agents/style_mixer.yaml
name: style_mixer
display_name: Style Mixer
description: Combines multiple style references

model:
  provider: gemini
  name: gemini-3.1-pro-preview

instruction: |
  Combine the artistic style and cinematography specs into a unified style guide.

inputs:
  - name: style_brief
    type: string
    source: context.style_brief

  - name: shot_brief
    type: string
    source: context.shot_brief

  - name: mood
    type: string
    source: context.metadata.mood
    optional: true

outputs:
  - name: combined_style
    type: string
    target: context.metadata.combined_style

type: llm_agent
```

---

## Best Practices

### 1. Agent Design

- **Single Responsibility**: Each agent should do one thing well
- **Clear Instructions**: Be explicit about expected input format and output format
- **Descriptive Names**: Use clear, descriptive names for inputs/outputs
- **Type Safety**: Specify correct types for inputs/outputs

### 2. HITL Configuration

- **Meaningful Labels**: Use clear, actionable labels for outputs and options
- **Helpful Messages**: Provide context in thinking messages
- **Logical Flow**: Ensure `next_agent` creates a coherent workflow

### 3. Pipeline Organization

- **Named Pipelines**: Create multiple pipeline configurations for different use cases
- **Comments**: Add comments to explain complex configurations
- **Version Control**: Track changes to YAML files in git

### 4. Testing

- **Start Simple**: Test agents individually before adding to pipeline
- **Incremental**: Add one agent at a time to pipeline
- **Fallbacks**: Use `fallback` and `optional` for robustness

---

## Troubleshooting

### Agent Not Found

**Error:** `FileNotFoundError: Agent config not found`

**Solution:** Ensure the YAML file exists in `backend/agents/` and the filename matches the agent name in `pipeline.yaml`

### Invalid YAML Syntax

**Error:** `yaml.scanner.ScannerError`

**Solution:** Check YAML syntax. Common issues:
- Incorrect indentation (use 2 spaces, not tabs)
- Missing colons after keys
- Unquoted strings with special characters

### Context Field Not Found

**Error:** `AttributeError: 'PipelineContext' object has no attribute 'field_name'`

**Solution:**
- Check that the field exists in `PipelineContext` dataclass
- Ensure previous agents have set the field
- Add `optional: true` if field might not exist

### HITL Not Working

**Problem:** Review gate not appearing

**Solution:**
- Check `hitl.enabled: true`
- Verify `review_stage` matches pattern `awaiting_{agent}_review`
- Ensure frontend can extract agent name from stage

---

## Advanced Topics

### Custom Agent Types

To add a new agent type, modify `models/yaml_loader.py`:

```python
def run(self, ctx: PipelineContext) -> PipelineContext:
    if self.config.agent_type == "my_custom_type":
        return self._run_my_custom_agent(ctx)
    # ...

def _run_my_custom_agent(self, ctx: PipelineContext) -> PipelineContext:
    # Your custom logic here
    pass
```

### Environment-Based Configuration

Use environment variables to switch configurations:

```yaml
model:
  name: ${MODEL_NAME:-gemini-3.1-pro-preview}  # Default if not set
```

### Conditional Logic

Use pipeline alternatives for different scenarios:

```yaml
pipelines:
  development:
    agents: [planner, generator]
    settings:
      enable_hitl: false

  production:
    agents: [planner, art_director, dop, generator, critic]
    settings:
      enable_hitl: true
```

---

## Summary

The YAML configuration system provides:

✅ **Easy Configuration**: Modify agent behavior without code changes
✅ **Modularity**: Add/remove agents by editing pipeline.yaml
✅ **Flexibility**: Create multiple pipeline configurations
✅ **HITL Support**: Built-in human review gates
✅ **Type Safety**: Explicit input/output types
✅ **Extensibility**: Easy to add new agent types

For more examples, see the existing agent configurations in `backend/agents/`.
