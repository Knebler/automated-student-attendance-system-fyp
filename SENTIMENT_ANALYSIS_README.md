# Automated Testimonial Sentiment Analysis

## Overview
The system now includes automated sentiment analysis to filter inappropriate testimonials before they reach the manual review stage. This helps maintain quality and professionalism of published testimonials.

## How It Works

### 1. Sentiment Analysis
When a user submits a testimonial, the system automatically analyzes the content using VADER (Valence Aware Dictionary and sEntiment Reasoner) sentiment analysis:

- **Positive sentiment**: Testimonials with positive language are allowed through
- **Neutral sentiment**: Balanced or factual testimonials are accepted
- **Negative sentiment**: Highly negative testimonials are automatically rejected

### 2. Profanity Detection
The system checks for inappropriate language using a predefined list of vulgar words and phrases. Any testimonial containing profanity is automatically rejected.

### 3. Automatic Status Assignment

#### Automatically Rejected If:
1. **Contains profanity** - Any vulgar or inappropriate language
2. **Overly negative sentiment** - Compound sentiment score below -0.5
3. **High negative content** - Negative component score above 0.5

#### Status Flow:
- **Appropriate content** → Status: `pending` (awaits platform manager approval)
- **Inappropriate content** → Status: `rejected` (user notified with reason)

## Technical Implementation

### Sentiment Score Interpretation
VADER provides a compound score ranging from -1 (most negative) to +1 (most positive):
- **+0.5 to +1.0**: Very positive
- **+0.0 to +0.5**: Positive
- **-0.0 to +0.0**: Neutral
- **-0.5 to -0.0**: Negative
- **-1.0 to -0.5**: Very negative (automatically rejected)

### Components
1. **TestimonialControl.analyze_testimonial_sentiment()**
   - Performs sentiment analysis
   - Checks for profanity
   - Returns detailed analysis results

2. **Modified Submission Flow**
   - Analyzes content before saving
   - Sets appropriate status
   - Provides user feedback

## User Experience

### For Users Submitting Testimonials
- Positive/constructive testimonials → "Thank you! Your testimonial will be reviewed."
- Inappropriate testimonials → Clear feedback explaining why it was rejected

### For Platform Managers
- Reduced manual review workload
- Only appropriate testimonials reach pending queue
- Can still view rejected testimonials for monitoring

## Testing
Run the sentiment analysis test script:
```bash
python test_sentiment_analysis.py
```

This will test various scenarios:
- Positive testimonials
- Neutral testimonials
- Negative testimonials
- Testimonials with profanity
- Constructive criticism

## Configuration

### Adjusting Sensitivity
Edit `application/controls/testimonial_control.py`:

```python
# Make more lenient (allow more negative content)
if compound_score < -0.7:  # instead of -0.5
    is_appropriate = False

# Make more strict (reject less negative content)
if compound_score < -0.3:  # instead of -0.5
    is_appropriate = False
```

### Managing Profanity List
Update `PROFANITY_LIST` in `testimonial_control.py`:
```python
PROFANITY_LIST = [
    # Add or remove words as needed
    'word1', 'word2', 'word3'
]
```

## Benefits
1. ✅ Automatically filters inappropriate content
2. ✅ Reduces manual review workload
3. ✅ Maintains professional image
4. ✅ Provides clear feedback to users
5. ✅ Protects platform reputation

## Future Enhancements
- Machine learning-based classification
- Language-specific sentiment analysis
- Customizable profanity filters per institution
- Appeal process for rejected testimonials
- Spam detection
