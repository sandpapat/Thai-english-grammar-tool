# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application for an MSc dissertation in Computer Science with Speech and Language Processing. The application provides a Thai-to-English NLP pipeline with tense classification and grammar explanation, featuring comprehensive performance evaluation across two distinct testing methodologies.

## Project Structure

```
Website/
├── app/                          # Main application code
│   ├── pipeline.py              # NLP pipeline models
│   ├── templates/               # HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── result.html
│   │   ├── tenses.html
│   │   ├── performance.html
│   │   ├── classifier_performance.html
│   │   └── pipeline_performance.html
│   └── static/                  # Static files (CSS, JS, images)
│       └── css/
│           └── style.css
├── data/                        # Data files and datasets
│   ├── Confusion Matrix.csv
│   ├── Per-label Report.csv
│   └── tags.csv
├── docs/                        # Documentation
│   ├── CLAUDE.md               # Original project documentation
│   ├── model_evaluation_analysis.md
│   ├── BERT Classification score.docx
│   └── model_performance_showcase.html
├── config/                      # Configuration files (future use)
├── app.py                       # Main Flask application
└── requirements.txt             # Python dependencies
```

## Architecture

### Core Components

1. **NLP Pipeline** (`app/pipeline.py`)
   - `TyphoonTranslator`: Thai-to-English translation using Typhoon Translate 4B (GGUF model via llama-cpp)
   - `TenseClassifier`: Tense classification using pretrained XLM-RoBERTa (Transformers)
   - `GrammarExplainer`: Grammar explanation using Typhoon 2.1 4B Instruct (Transformers)
   - `ModelManager`: Coordinates all models with graceful error handling

2. **Web Application** (`app.py`)
   - Route `/`: Homepage with Thai text input form
   - Route `/predict`: Process input through pipeline and display results
   - Route `/tenses`: Display tense usage explanations
   - Route `/performance`: Combined view of both evaluation approaches
   - Route `/classifier-performance`: BERT classifier isolated testing results
   - Route `/pipeline-performance`: Full pipeline end-to-end evaluation results

3. **Data Flow**
   - Input: Thai sentence → Translation → Tense Classification → Grammar Explanation
   - Output format: Dictionary with translation, coarse/fine labels, and 3-section explanation

### Explanation Format
Explanations follow this structure:
```
[SECTION 1: Context Cues]
[SECTION 2: Tense Decision]
[SECTION 3: Grammar Tips]
```

## Performance Evaluation Framework

The application implements a **dual evaluation approach** to comprehensively assess system performance:

### 1. Isolated Classifier Testing
- **Route**: `/classifier-performance`
- **Data Source**: `data/Per-label Report.csv`
- **Sample Size**: 469 samples across 24 fine-grained tense classes
- **Focus**: Pure XLM-RoBERTa classification performance without pipeline overhead
- **Key Metrics**: 94.7% accuracy, 91.3% macro F1, 94.6% weighted F1
- **Purpose**: Establishes baseline classifier capability in ideal conditions

### 2. End-to-End Pipeline Testing
- **Route**: `/pipeline-performance`
- **Data Source**: `docs/model_evaluation_analysis.md`
- **Sample Size**: 96 samples with 7 evaluation criteria
- **Focus**: Complete system evaluation including translation, classification, and explanation
- **Key Metrics**: B+ grade (85% overall), component-wise performance analysis
- **Purpose**: Measures real-world system performance and user experience

### Performance Comparison
- **Isolated Classification**: 94.7% accuracy (optimal conditions)
- **Pipeline Classification**: 74% accuracy (real-world conditions)
- **Performance Gap**: 20.7% degradation due to translation errors and context loss
- **Overall Assessment**: B+ grade demonstrating functional educational tool

## Template Structure and Navigation

### Template Files
- `app/templates/base.html`: Main layout with Bootstrap dropdown navigation
- `app/templates/index.html`: Homepage with Thai text input form
- `app/templates/result.html`: Displays pipeline processing results
- `app/templates/tenses.html`: Tense usage explanations and examples
- `app/templates/performance.html`: Combined view of both evaluation approaches
- `app/templates/classifier_performance.html`: Green-themed isolated classifier results
- `app/templates/pipeline_performance.html`: Blue-themed full pipeline evaluation

### Navigation Structure
The performance section uses a Bootstrap dropdown menu:
- **Performance** (dropdown)
  - **BERT Classifier**: Isolated testing results (469 samples)
  - **Full Pipeline**: End-to-end evaluation (96 samples)
  - **Combined View**: Integrated presentation of both approaches

## Data Sources and Evaluation Datasets

### data/Per-label Report.csv
- **Content**: Detailed per-class performance metrics for XLM-RoBERTa classifier
- **Format**: Label, Precision, Recall, F1-Score, Support columns
- **Usage**: Populates classifier_performance.html with isolated test results
- **Highlights**: 6 perfect classes (F1=1.000), 4 challenging classes requiring improvement

### docs/model_evaluation_analysis.md
- **Content**: Comprehensive pipeline evaluation with 7 metrics
- **Metrics**: Translation fluency, meaning preservation, tense classification, explanation quality, etc.
- **Usage**: Drives pipeline_performance.html with end-to-end results
- **Assessment**: B+ overall grade with detailed component analysis

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask application in development mode
python app.py

# Run Flask with specific port
flask run --port 5000

# Run in production mode
export FLASK_ENV=production
python app.py
```

## Model Integration Notes

- **Translator**: GGUF model loaded via llama-cpp-python, requires llama.cpp backend
- **Classifier & Explainer**: Both use Transformers library from Hugging Face
- Models are loaded with error handling to allow graceful degradation
- Each model can fail independently without breaking the entire pipeline
- Consider memory usage as two Transformers models + one GGUF model will be loaded

## Testing Approach

### Component Testing
1. Use mock implementations in `app/pipeline.py` if actual models aren't available
2. Test each component (translation, classification, explanation) independently
3. Verify explanation parsing regex handles all three sections correctly

### Performance Evaluation
1. **Isolated Testing**: Run classifier against `data/Per-label Report.csv` data for baseline performance
2. **Pipeline Testing**: Evaluate complete system using `docs/model_evaluation_analysis.md` criteria
3. **Comparison Analysis**: Compare isolated vs pipeline performance to identify bottlenecks
4. **Benchmarks**: 
   - Classifier accuracy >90% (achieved: 94.7%)
   - Pipeline overall grade B+ (achieved: 85%)
   - Translation fluency >90% (achieved: 93.2%)

### Performance Interpretation Guidelines
- **94.7% Classifier Accuracy**: Excellent baseline capability in isolated conditions
- **74% Pipeline Classification**: Real-world performance with translation context
- **20.7% Performance Gap**: Expected degradation due to translation errors and pipeline complexity
- **B+ Overall Grade**: Suitable for dissertation requirements and demonstrates functional educational tool

## Important Considerations

- The application expects a `Hybrid4BSystem` class with `full_pipeline(thai_text)` method
- Bootstrap 5 is used for styling via CDN with dropdown navigation components
- Flash messages provide user feedback for errors
- All file paths should be absolute, not relative
- The explanation sections are parsed using regex pattern matching
- Performance pages use distinct color themes (green for classifier, blue for pipeline)
- Navigation dropdown requires Bootstrap JavaScript for proper functionality
- Evaluation data should be interpreted in context of the dual testing approach
- The 20% performance gap between isolated and pipeline testing is expected and documented

## Performance Page Color Coding
- **Green Theme**: `classifier_performance.html` - Isolated BERT classifier testing
- **Blue/Purple Theme**: `pipeline_performance.html` - Full pipeline evaluation
- **Mixed Theme**: `performance.html` - Combined view of both approaches

This color coding helps users immediately distinguish between the two evaluation methodologies.

## File Organization Notes

- **app/**: Contains all application code (pipeline, templates, static files)
- **data/**: Contains CSV files and datasets used for evaluation
- **docs/**: Contains documentation files including analysis and reports
- **config/**: Reserved for configuration files (currently empty)
- **Root**: Contains main Flask app file and requirements.txt