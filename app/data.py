"""
Data management for performance metrics and configurations
"""


def get_performance_data(pipeline_mode=False):
    """
    Get performance data for different modes
    
    Args:
        pipeline_mode (bool): If True, return pipeline-specific metrics
        
    Returns:
        dict: Performance data structure
    """
    base_data = {
        'translator': {
            'name': 'Typhoon Translate 4B',
            'type': 'GGUF via llama-cpp',
            'metrics': {
                'BLEU Score': 'TBD',
                'Average Latency': '1.20s' if pipeline_mode else 'TBD ms',
                'Memory Usage': 'TBD GB'
            }
        },
        'classifier': {
            'name': 'XLM-RoBERTa',
            'type': 'Transformers',
            'metrics': {
                'Accuracy': '94.7%',
                'Macro F1 Score': '91.3%',
                'Weighted F1 Score': '94.6%'
            },
            'confusion_matrix': {
                'Past': {'Past': 99.77, 'Present': 0.23, 'Future': 0.00},
                'Present': {'Past': 0.34, 'Present': 99.49, 'Future': 0.17},
                'Future': {'Past': 0.00, 'Present': 0.00, 'Future': 100.00}
            },
            'top_performing_labels': [
                {'label': 'BEFOREPAST', 'f1': 1.000},
                {'label': 'DURATION', 'f1': 1.000},
                {'label': 'JUSTFIN', 'f1': 1.000},
                {'label': 'LONGFUTURE', 'f1': 1.000},
                {'label': 'SINCEFOR', 'f1': 1.000},
                {'label': 'WILLCONTINUEINFUTURE', 'f1': 1.000}
            ],
            'challenging_labels': [
                {'label': 'NOWADAYS', 'f1': 0.308},
                {'label': 'PROMISE', 'f1': 0.600},
                {'label': 'RIGHTNOW', 'f1': 0.824},
                {'label': 'SAYING', 'f1': 0.833}
            ]
        },
        'explainer': {
            'name': 'Typhoon 2.1 4B Instruct',
            'type': 'Transformers',
            'metrics': {
                'Quality Score': 'TBD',
                'Average Latency': '10.26s' if pipeline_mode else 'TBD ms',
                'Memory Usage': 'TBD GB'
            }
        },
        'pipeline': {
            'total_latency': '11.47s' if pipeline_mode else 'TBD ms',
            'success_rate': 'TBD%',
            'requests_processed': 96 if pipeline_mode else 0
        }
    }
    
    if pipeline_mode:
        base_data['pipeline']['note'] = 'Timing excludes cold start response'
    
    return base_data