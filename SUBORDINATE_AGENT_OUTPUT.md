# Subordinate Agent Output Structure

## Overview
Subordinate agents use the **ReAct (Reasoning + Acting) framework** with GPT-4o to analyze research papers and extract key information.

## ReAct Framework Process

Each agent follows this reasoning process:

1. **THOUGHT**: Analyze the research significance and context
2. **ACTION**: Extract key information systematically
3. **OBSERVATION**: Identify patterns, findings, and contributions
4. **REFLECTION**: Assess novelty, impact, and limitations

## Output JSON Structure

Each analyzed paper produces the following JSON structure:

```json
{
  "summary": "Brief 2-3 sentence overview of the paper",
  "key_points": [
    "Main contribution 1",
    "Main contribution 2",
    "Key finding 1",
    "Methodology insight",
    "Novel aspect"
  ],
  "citations": [
    {
      "title": "paper title",
      "authors": "author names if available",
      "year": "publication year if available",
      "source": "URL to the paper"
    }
  ],
  "metadata": {
    "core_ideas": ["idea1", "idea2"],
    "methodology": "brief description of research methods",
    "key_findings": ["finding1", "finding2"],
    "novelty": "what's new or innovative",
    "limitations": ["limitation1", "limitation2"],
    "relevance_score": 8,
    "reasoning": "ReAct thought process summary"
  }
}
```

## Field Descriptions

### Top-Level Fields

- **summary**: Concise 2-3 sentence overview capturing the essence of the research
- **key_points**: Array of 3-5 main contributions, findings, and insights
- **citations**: Array of citation objects with bibliographic information

### Metadata Fields

- **core_ideas**: Main concepts and themes explored in the paper
- **methodology**: Research approach and methods used
- **key_findings**: Primary results and discoveries
- **novelty**: Novel aspects and innovations
- **limitations**: Research gaps, constraints, or acknowledged limitations
- **relevance_score**: 0-10 score indicating relevance to the query
- **reasoning**: Summary of the ReAct framework thought process

## Example Output

```json
{
  "summary": "The paper explores the integration of big data and machine learning in healthcare, emphasizing their potential to transform healthcare delivery and outcomes.",
  "key_points": [
    "Provides comprehensive overview of big data and ML in healthcare",
    "Discusses potential benefits and challenges",
    "Machine learning enhances data analysis and decision-making",
    "Uses narrative review approach to synthesize literature",
    "Makes complex technologies accessible to healthcare professionals"
  ],
  "citations": [
    {
      "title": "Big data and machine learning in health care",
      "authors": "Not specified",
      "year": "Not specified",
      "source": "https://jamanetwork.com/journals/jama/article-abstract/2675024"
    }
  ],
  "metadata": {
    "core_ideas": [
      "Integration of big data and machine learning in healthcare",
      "Impact on healthcare delivery and outcomes"
    ],
    "methodology": "Narrative review of existing literature",
    "key_findings": [
      "Machine learning enhances data analysis in healthcare",
      "Big data can improve decision-making processes"
    ],
    "novelty": "Demystifies complex technologies for healthcare professionals",
    "limitations": [
      "Lacks empirical data or case studies",
      "Focuses primarily on theoretical implications"
    ],
    "relevance_score": 8,
    "reasoning": "Addresses growing interest in leveraging technology to improve healthcare by breaking down complex concepts for practitioners"
  }
}
```

## Usage in System

Subordinate agents:
1. Accept a list of research papers from the Supervisor
2. Process each paper independently using the ReAct framework
3. Extract information using GPT-4o with structured prompting
4. Return array of analysis objects in the specified JSON format
5. Results are aggregated by Supervisor and sent to Summarizer

## Benefits of ReAct Framework

- **Systematic Analysis**: Structured reasoning process ensures thorough analysis
- **Explainable**: Reasoning field captures the thought process
- **Comprehensive**: Covers all aspects from methodology to limitations
- **Actionable**: Key points and findings are clearly highlighted
- **Contextual**: Reasoning provides context for the analysis
