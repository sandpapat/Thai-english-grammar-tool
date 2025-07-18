# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application for an MSc dissertation in Computer Science with Speech and Language Processing. The application provides a Thai-to-English NLP pipeline with tense classification and grammar explanation, featuring comprehensive performance evaluation across two distinct testing methodologies.

**Latest Updates (2025-01-18):**
- ✅ **Modern UI Redesign**: Sleek glassmorphism effects, gradients, and contemporary aesthetics
- ✅ **Rebranding**: Introduced "Thaislate" brand identity throughout the application
- ✅ **Typography Standardization**: Unified font system using Prompt for all content
- ✅ **Enhanced Profanity Filter**: Comprehensive Thai profanity detection with educational messaging
- ✅ **About Us Page**: Bilingual content showcasing mission, technology, and team
- ✅ **Dark Mode Fixes**: Improved contrast and readability in dark mode for all components

## Project Structure

```
Website/
├── app/                          # Main application code (REFACTORED)
│   ├── __init__.py              # Application factory pattern
│   ├── routes.py                # Main blueprint routes
│   ├── auth.py                  # Authentication blueprint
│   ├── models.py                # Database models
│   ├── pipeline.py              # NLP pipeline models
│   ├── validation.py            # Input validation
│   ├── utils.py                 # Utility functions (NEW)
│   ├── data.py                  # Data management (NEW)
│   ├── templates/               # HTML templates (ENHANCED)
│   │   ├── base.html           # Base template with dark mode & Thaislate branding
│   │   ├── index.html          # Homepage with modern hero section & glassmorphism
│   │   ├── result.html         # Results page with proper Thai font support
│   │   ├── tenses.html         # Tense explanations with Thai language attributes
│   │   ├── about.html          # Bilingual About Us page (NEW)
│   │   ├── performance.html    # Performance overview
│   │   ├── classifier_performance.html # BERT results with dark mode fixes
│   │   └── pipeline_performance.html   # Pipeline results
│   └── static/                  # Static files (ENHANCED)
│       └── css/
│           └── style.css       # Modern design with glassmorphism + Prompt font
├── data/                        # Data files and datasets
│   ├── Confusion Matrix.csv
│   ├── Per-label Report.csv
│   └── tags.csv
├── docs/                        # Documentation
│   ├── CLAUDE.md               # This file (UPDATED)
│   ├── model_evaluation_analysis.md
│   ├── BERT Classification score.docx
│   └── model_performance_showcase.html
├── config.py                    # Configuration classes (NEW)
├── gunicorn_config.py          # Production server config (NEW)
├── deployment_guide.md         # Deployment instructions (NEW)
├── app.py                       # Main Flask application (SIMPLIFIED)
└── requirements.txt             # Python dependencies (UPDATED)
```

## Architecture

### Core Components

1. **NLP Pipeline** (`app/pipeline.py`)
   - `TyphoonTranslator`: Thai-to-English translation using Typhoon Translate 4B (GGUF model via llama-cpp)
   - `TenseClassifier`: Tense classification using pretrained XLM-RoBERTa (Transformers)
   - `GrammarExplainer`: Grammar explanation using Typhoon 2.1 4B Instruct (Transformers)
   - `ModelManager`: Coordinates all models with graceful error handling

2. **Web Application** (Refactored with Blueprint Architecture)
   - **Main Blueprint** (`app/routes.py`):
     - Route `/`: Homepage with modern hero section and glassmorphism cards
     - Route `/predict`: Process input through pipeline and display results
     - Route `/validate`: Real-time input validation API
     - Route `/tenses`: Display tense usage explanations with Thai language support
     - Route `/about`: Bilingual About Us page with team and technology info
     - Route `/performance`: Combined view of both evaluation approaches
     - Route `/classifier-performance`: BERT classifier isolated testing results
     - Route `/pipeline-performance`: Full pipeline end-to-end evaluation results
   - **Authentication Blueprint** (`app/auth.py`):
     - Route `/login`: User authentication with 5-digit pseudocode
     - Route `/logout`: User logout functionality
   - **Application Factory** (`app/__init__.py`):
     - Configurable Flask app creation
     - Blueprint registration and extension initialization

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

# Run in production mode with Gunicorn
gunicorn -c gunicorn_config.py app:app

# Run with environment configuration
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here
python app.py

# Create database tables
python -c "from app import create_app; app = create_app(); app.app_context().push(); from app.models import db; db.create_all()"
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

- The application uses Flask Blueprint architecture with `main` and `auth` blueprints
- All routes are now prefixed with blueprint names (e.g., `main.index`, `auth.login`)
- Bootstrap 5 is used for styling via CDN with enhanced dark mode support
- Dark mode toggle is available in the navigation bar for all users
- CSS variables enable seamless theme switching with proper color contrast
- Flash messages provide user feedback with improved accessibility
- All file paths should be absolute, not relative
- The explanation sections are parsed using regex pattern matching in `app/utils.py`
- Performance pages use distinct color themes (green for classifier, blue for pipeline)
- Navigation dropdown requires Bootstrap JavaScript for proper functionality
- Evaluation data should be interpreted in context of the dual testing approach
- The 20% performance gap between isolated and pipeline testing is expected and documented
- Real-time validation provides immediate feedback as users type Thai text
- Keyboard shortcuts enhance accessibility: Alt+S (focus), Alt+Enter (submit), Escape (clear)

## New Features Available

### Modern Design & Branding
- **Thaislate Brand Identity**: Complete rebranding with modern logo and consistent naming
- **Glassmorphism Effects**: Contemporary UI design with transparency and blur effects
- **Gradient Backgrounds**: Subtle background patterns enhancing visual appeal
- **Modern Typography**: Universal Prompt font for consistent, readable text across all languages

### Dark Mode
- Click the moon/sun icon in the navigation to toggle between light and dark themes
- User preference is automatically saved and restored on future visits
- System dark mode preference is automatically detected and applied
- Improved contrast ratios for better readability in all components

### Enhanced Accessibility
- Complete keyboard navigation support throughout the application
- Screen reader friendly with proper ARIA labels and semantic HTML
- Skip-to-content link for keyboard users
- High contrast support and reduced motion preferences respected

### Mobile Optimization
- Touch-friendly interface with 44px minimum touch targets
- Responsive design that works seamlessly on all device sizes
- Optimized typography and spacing for mobile devices
- Progressive enhancement with smooth animations and transitions

### Improved User Experience
- Real-time validation with live feedback
- Enhanced progress indicators during processing
- Clean percentage display (whole numbers instead of decimals)
- Fixed all navigation routing issues
- Better error handling and user feedback

### Content & Features
- **Bilingual About Page**: Comprehensive English/Thai about page with team information
- **Enhanced Profanity Filter**: Improved Thai profanity detection with educational messaging
- **Language Support**: Proper Thai language attributes throughout the application

## Performance Page Color Coding
- **Green Theme**: `classifier_performance.html` - Isolated BERT classifier testing
- **Blue/Purple Theme**: `pipeline_performance.html` - Full pipeline evaluation
- **Mixed Theme**: `performance.html` - Combined view of both approaches

This color coding helps users immediately distinguish between the two evaluation methodologies.

## Recent Improvements (2025-01-18)

### 1. **Refactored Architecture**
- **Application Factory Pattern**: Implemented `create_app()` function for better configuration management
- **Blueprint Structure**: Separated routes into logical blueprints (`main`, `auth`)
- **Modular Design**: Split large functions into focused utility modules
- **Configuration Management**: Added `config.py` for environment-specific settings

### 2. **Enhanced Mobile Experience**
- **Mobile-First CSS**: Responsive design starting from mobile screens
- **Touch-Friendly**: 44px minimum touch targets for all interactive elements
- **Progressive Enhancement**: Improved visual feedback and animations
- **Responsive Typography**: Dynamic font scaling across all device sizes
- **Optimized Navigation**: Collapsible menu with improved mobile interactions

### 3. **Comprehensive Accessibility**
- **WCAG 2.1 Compliance**: Full accessibility support with proper ARIA labels
- **Keyboard Navigation**: Complete keyboard support with custom shortcuts:
  - `Alt + S`: Focus on text input
  - `Alt + Enter`: Submit form
  - `Escape`: Clear text input
- **Screen Reader Support**: Semantic HTML and proper landmarks
- **Skip Navigation**: Skip-to-content link for keyboard users
- **Focus Management**: Visible focus indicators and logical tab order

### 4. **Dark Mode Implementation**
- **Complete Theme System**: CSS variables for seamless theme switching
- **User Preference Persistence**: localStorage saves theme choice
- **System Integration**: Automatic detection of system dark mode preference
- **Smooth Transitions**: All theme changes have smooth animations
- **Accessibility**: Proper color contrast ratios in both themes
- **Toggle Interface**: Moon/sun icon toggle in navigation bar

### 5. **Code Quality Improvements**
- **Utility Functions**: Extracted `format_explanation_content()` to `app/utils.py`
- **Data Management**: Centralized performance data in `app/data.py`
- **Error Handling**: Improved error messages and validation feedback
- **Route Fixes**: Fixed all endpoint routing issues (main.index, main.performance, etc.)
- **Percentage Display**: Clean integer display for Thai percentage validation

### 6. **Deployment Readiness**
- **Production Configuration**: Added `gunicorn_config.py` for production deployment
- **Deployment Guide**: Complete Google Cloud VM deployment instructions
- **Version Compatibility**: Fixed Flask/Werkzeug version compatibility issues
- **Environment Variables**: Proper configuration through environment variables

### 7. **User Experience Enhancements**
- **Real-time Validation**: Live feedback as user types Thai text
- **Progress Indicators**: Enhanced progress animations during processing
- **Form Validation**: Improved validation with proper error states
- **Navigation Improvements**: Fixed all broken navigation links
- **Loading States**: Better loading indicators and user feedback

## Typography and Font System

### Font Standardization
- **Universal Font**: All text uses Google Fonts "Prompt" for consistency
- **Language Support**: Prompt font supports both English and Thai characters excellently
- **Implementation**: CSS variables (`--font-universal`) ensure consistent font application
- **Fallback System**: Graceful degradation with system fonts if Prompt fails to load

### Font Application
```css
/* Universal Typography - Prompt for Everything */
--font-universal: 'Prompt', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* All elements use Prompt font */
* {
    font-family: var(--font-universal) !important;
}
```

### Language Attributes
- Thai text sections use `lang="th"` attributes for proper rendering
- English sections use `lang="en"` attributes for accessibility
- Proper language tagging improves screen reader support and search engine optimization

## File Organization Notes

- **app/**: Contains all application code (pipeline, templates, static files)
- **data/**: Contains CSV files and datasets used for evaluation
- **docs/**: Contains documentation files including analysis and reports
- **config/**: Reserved for configuration files (currently empty)
- **Root**: Contains main Flask app file and requirements.txt