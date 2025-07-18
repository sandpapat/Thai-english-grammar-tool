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
    # Common time markers and grammar keywords
    keyword_patterns = [
        (r'\b(yesterday|today|tomorrow|now|then)\b', 'time-marker'),
        (r'\b(last week|last month|last year|next week|next month|next year)\b', 'time-marker'),
        (r'\b(ago|before|after|since|until)\b', 'time-marker'),
        (r'\b(always|usually|often|sometimes|never|rarely)\b', 'frequency-marker'),
        (r'\b(every day|every week|every month|every year)\b', 'frequency-marker'),
        (r'\b(Subject|Verb|Object|V1|V2|V3|Past Simple|Present Simple|Future Simple)\b', 'grammar-term'),
        (r'\b(market|school|hospital|restaurant|office|home)\b', 'place-marker')
    ]
    
    # Apply keyword highlighting
    for pattern, css_class in keyword_patterns:
        content = re.sub(pattern, rf'<span class="keyword-highlight {css_class}">\1</span>', content, flags=re.IGNORECASE)
    
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
        
        # Check if it's a bullet point
        if line.startswith('* ') and len(line) > 2:
            if in_paragraph:
                formatted_lines.append('</p>')
                in_paragraph = False
            bullet_content = line[2:].strip()
            formatted_lines.append(f'<li class="thai-bullet mb-2">{bullet_content}</li>')
        
        # Check if it's a structural header
        elif (line.endswith(':') and 
              (any(word in line for word in ['โครงสร้าง', 'ตัวอย่าง', 'วิธี', 'คำศัพท์', 'Subject', 'Verb']) or
               line.count(' ') <= 3)):
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