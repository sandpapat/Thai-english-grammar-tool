"""
Utility functions for text processing and formatting
"""
import re


def format_explanation_content(content):
    """
    Format explanation content for better readability
    
    Args:
        content (str): Raw explanation content
        
    Returns:
        str: Formatted HTML content
    """
    if not content:
        return content
    
    # Clean up the raw content
    content = content.strip()
    
    # Remove HTML tags first
    content = re.sub(r'<[^>]+>', '', content)
    
    # Fix broken bold patterns like "**Text•*" or "**Text*"
    content = re.sub(r'\*\*([^*]+?)[•\*]*\*+', r'**\1**', content)
    
    # Clean up scattered bullet symbols and newlines (but preserve actual bullet points)
    content = re.sub(r'\n\s*[•\*]\s*\n', '\n', content)
    content = re.sub(r'^[•\*]\s*$', '', content, flags=re.MULTILINE)
    
    # Fix patterns where content is broken across lines
    content = re.sub(r'(\*\*[^*\n]+)\n\s*[•\*]\s*\n\s*\*', r'\1**', content)
    
    # Clean up multiple consecutive newlines
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # First pass: identify and mark special keywords for highlighting
    # Process in order of priority to prevent overlaps
    
    # Clean content first - add spaces around punctuation for better word boundaries
    content = re.sub(r'([.,;:!?])', r' \1 ', content)
    
    # Add spaces between Thai and English text for better parsing
    content = re.sub(r'([ก-๙])([A-Za-z])', r'\1 \2', content)
    content = re.sub(r'([A-Za-z])([ก-๙])', r'\1 \2', content)
    
    # Normalize whitespace
    content = re.sub(r'\s+', ' ', content)
    
    # Define patterns in order of priority (most specific first)
    keyword_patterns = [
        # Complex grammar terms first (most specific) - single capture group
        (r'\b(Future Simple Tense|Present Simple Tense|Past Simple Tense|Future Continuous Tense|Present Continuous Tense|Past Continuous Tense|Future Perfect Tense|Present Perfect Tense|Past Perfect Tense)\b', 'grammar-term'),
        (r'\b(Future Simple|Present Simple|Past Simple|Future Continuous|Present Continuous|Past Continuous|Future Perfect|Present Perfect|Past Perfect)\b', 'grammar-term'),
        # Perfect tenses
        (r'\b(Present Perfect|Past Perfect|Future Perfect)\b', 'grammar-term'),
        # Single tense components 
        (r'\b(Simple Tense|Continuous Tense|Perfect Tense)\b', 'grammar-term'),
        (r'\b(Simple|Continuous|Perfect)\b', 'grammar-term'),
        # Time expressions (compound first)
        (r'\b(last week|last month|last year|next week|next month|next year)\b', 'time-marker'),
        (r'\b(every day|every week|every month|every year)\b', 'frequency-marker'),
        # Single time markers  
        (r'\b(yesterday|today|tomorrow|now|then|ago|before|after|since|until)\b', 'time-marker'),
        # Grammar components (standalone Tense and other terms)
        (r'\b(Subject|Verb|Object|V1|V2|V3|Tense|have|has|been)\b', 'grammar-term'),
        # Modal verbs
        (r'\b(will|would|shall|should|can|could|may|might|must)\b', 'modal-verb'),
        # Frequency markers
        (r'\b(always|usually|often|sometimes|never|rarely)\b', 'frequency-marker'),
        # Place markers
        (r'\b(market|school|hospital|restaurant|office|home|store)\b', 'place-marker')
    ]
    
    # Apply highlighting with simple overlap prevention
    highlighted_content = content
    for pattern, css_class in keyword_patterns:
        # Apply highlighting only if the text isn't already highlighted
        def replace_func(match):
            matched_text = match.group(0)
            # Check if this text is already inside a span
            start_pos = match.start()
            text_before = highlighted_content[:start_pos]
            if '<span class="keyword-highlight' in text_before and '</span>' not in text_before[text_before.rfind('<span'):]:
                # We're inside a span, don't highlight
                return matched_text
            return f'<span class="keyword-highlight {css_class}">{matched_text}</span>'
        
        highlighted_content = re.sub(pattern, replace_func, highlighted_content, flags=re.IGNORECASE)
    
    content = highlighted_content
    
    # Add proper spacing around highlighted elements
    content = re.sub(r'(<span class="keyword-highlight[^"]*">[^<]+</span>)', r' \1 ', content)
    content = re.sub(r'\s+', ' ', content)  # Normalize whitespace again
    
    # Process line by line for proper structure
    lines = content.split('\n')
    formatted_lines = []
    in_paragraph = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            continue
        
        # Handle bold text (but preserve highlighted keywords inside)
        line = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', line)
        
        # Ensure proper spacing between highlighted elements and Thai text
        line = re.sub(r'(<span[^>]+>[^<]+</span>)\s*([ก-๙])', r'\1 \2', line)
        line = re.sub(r'([ก-๙])\s*(<span[^>]+>[^<]+</span>)', r'\1 \2', line)
        
        # Check if it's a bullet point
        if line.startswith('* ') and len(line) > 2:
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            bullet_content = line[2:].strip()
            formatted_lines.append(f'<li class="thai-bullet mb-2">{bullet_content}</li>')
        
        # Check if it's a structural header (Thai or English)
        elif (line.endswith(':') and 
              (any(word in line for word in ['โครงสร้าง', 'ตัวอย่าง', 'วิธี', 'คำศัพท์', 'Subject', 'Verb', 'Future', 'Simple', 'วิธีจำง่าย']) or
               line.count(' ') <= 4)):
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            formatted_lines.append(f'<h6 class="grammar-header mt-3 mb-2">{line}</h6>')
        
        # Check if line starts with Thai example indicators
        elif line.startswith('ตัวอย่าง:') or line.startswith('เช่น:'):
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            formatted_lines.append(f'<p class="example-text mb-2">{line}</p>')
        
        # Check if it's a standalone grammar term or definition
        elif any(term in line for term in ['Future Simple', 'Future Continuous', 'Future Perfect']) and ':' in line:
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            formatted_lines.append(f'<div class="grammar-definition mb-3">{line}</div>')
        
        # Regular content line
        else:
            if not in_paragraph and not line.startswith('<'):
                formatted_lines.append('<p class="explanation-paragraph mb-3">')
                in_paragraph = True
            
            # Add line with proper spacing
            if in_paragraph and len(formatted_lines) > 0 and not formatted_lines[-1].endswith('>'):
                formatted_lines.append('<br>')
            formatted_lines.append(line)
    
    # Close any open paragraph
    if in_paragraph:
        formatted_lines.append('</p>')
    
    # Group consecutive list items into proper <ul> tags
    final_html = []
    in_list = False
    
    for line in formatted_lines:
        if line.startswith('<li'):
            if not in_list:
                final_html.append('<ul class="thai-list">')
                in_list = True
            final_html.append('  ' + line)
        else:
            if in_list:
                final_html.append('</ul>')
                in_list = False
            final_html.append(line)
    
    # Close any remaining list
    if in_list:
        final_html.append('</ul>')
    
    # Join all HTML elements
    result = '\n'.join(final_html)
    
    # Final cleanup - ensure no empty paragraphs
    result = re.sub(r'<p[^>]*>\s*</p>', '', result)
    
    return result


def parse_explanation(explanation_text):
    """
    Parse explanation into sections based on [SECTION X: ...] markers
    
    Args:
        explanation_text (str): Raw explanation text
        
    Returns:
        dict: Parsed sections with titles and formatted content
    """
    sections = {}
    
    # Pattern to match sections
    pattern = r'\[SECTION (\d+): ([^\]]+)\](.*?)(?=\[SECTION|\Z)'
    matches = re.findall(pattern, explanation_text, re.DOTALL)
    
    for match in matches:
        section_num = match[0]
        section_title = match[1].strip()
        section_content = match[2].strip()
        sections[f'section_{section_num}'] = {
            'title': section_title,
            'content': format_explanation_content(section_content)
        }
    
    # If no sections found, return the full text as a single section
    if not sections:
        sections['section_1'] = {
            'title': 'Explanation',
            'content': format_explanation_content(explanation_text)
        }
    
    return sections