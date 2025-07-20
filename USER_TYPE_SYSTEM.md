# User Type System Documentation

## Overview

The application now supports two distinct user types: **Normal** and **Proficient**. While both user types have identical access to the core functionality, Proficient users have additional capabilities for rating and providing feedback on the system's performance.

## User Types

### Normal Users
- **Pseudocode Range**: 00001-89999
- **Badge Color**: Gray ("Normal")
- **Capabilities**: Full access to translation, classification, and explanation features
- **UI**: Standard interface without rating components

### Proficient Users  
- **Pseudocode Range**: 90000-99999 (automatically detected)
- **Badge Color**: Yellow ("Proficient") 
- **Capabilities**: All Normal user features + rating system access
- **UI**: Additional rating interface on results page

## Features

### Navigation Bar
- Displays: "Welcome [PSEUDOCODE]! (Normal/Proficient)"
- Color-coded badges distinguish user types
- User type information in dropdown menu

### Rating System (Proficient Users Only)
- **Location**: Bottom of results page
- **Components**:
  - 5-star rating for Translation Quality
  - 5-star rating for Overall Quality  
  - Optional comments field
  - Hide/show toggle functionality

### Rating Data Storage
- **Database Table**: `ratings`
- **Fields**: user_id, input_thai, translation_text, ratings, comments, timestamp
- **Privacy**: Only stores necessary data for analysis

## Test Users

### Normal Users
- `12345` - Standard user for testing normal functionality
- `67890` - Additional normal user

### Proficient Users  
- `90001` - Test proficient user with rating capabilities
- `91234` - Additional proficient user

## Database Schema

### Updated `pseudocodes` table
```sql
- user_type: ENUM('normal', 'proficient') DEFAULT 'normal'
```

### New `ratings` table
```sql
- id: INTEGER PRIMARY KEY
- user_id: INTEGER (FK to pseudocodes)
- input_thai: TEXT (original Thai input)
- translation_text: TEXT (translation that was rated)
- translation_rating: INTEGER (1-5 scale)
- overall_quality_rating: INTEGER (1-5 scale) 
- comments: TEXT (optional feedback)
- timestamp: DATETIME
```

## API Endpoints

### `/api/submit-rating` (POST)
- **Authentication**: Required (proficient users only)
- **Payload**: JSON with rating data
- **Response**: Success/error status
- **Validation**: Ratings must be 1-5, user must be proficient

## Implementation Details

### Automatic User Type Detection
- Users with pseudocodes starting with "9" are automatically marked as proficient
- This can be modified in `Pseudocode.create_pseudocode()` method

### Front-End Rating Interface
- Star rating system with hover effects
- Real-time validation and feedback
- AJAX submission with loading states
- Toggle visibility option

### Security Considerations
- Rating submission restricted to proficient users
- Input validation on both client and server side
- Error handling with user-friendly messages
- Database transaction safety

## Usage Instructions

1. **For Normal Users**:
   - Log in with any 5-digit code (00001-89999)
   - Use the system normally
   - No rating interface will appear

2. **For Proficient Users**:
   - Log in with codes starting with "9" (90001, 91234, etc.)
   - Complete a translation analysis
   - Scroll to bottom of results page
   - Rate translation quality and overall quality
   - Optionally add comments
   - Submit rating or hide the interface

## Future Enhancements

- **Rating Analytics Dashboard**: Aggregate rating data visualization
- **Advanced User Management**: Manual user type assignment
- **Rating History**: View past ratings for proficient users
- **Export Functionality**: Download rating data for analysis
- **Multi-language Rating Interface**: Thai language support for rating forms

## Maintenance

### Adding New User Types
1. Update `UserType` enum in `models.py`
2. Modify navigation template for new badge styling
3. Update user creation logic as needed

### Database Migrations
- Use `migrate_user_types.py` for future schema changes
- Always backup database before migrations
- Test migrations on development data first