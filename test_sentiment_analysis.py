"""
Test script for testimonial sentiment analysis
"""
from application.controls.testimonial_control import TestimonialControl

def test_testimonial_sentiment():
    """Test various testimonial scenarios"""
    
    test_cases = [
        {
            "name": "Positive testimonial",
            "content": "This is an amazing system! It has greatly improved our attendance tracking and made our lives so much easier. Highly recommend!",
            "expected": "approved"
        },
        {
            "name": "Neutral testimonial",
            "content": "The system works as expected. It does what it's supposed to do. Some features could be improved.",
            "expected": "approved"
        },
        {
            "name": "Negative testimonial",
            "content": "This system is terrible, awful, and completely useless. Worst experience ever. Waste of money and time.",
            "expected": "rejected"
        },
        {
            "name": "Testimonial with profanity",
            "content": "This damn system is shit and doesn't work properly. What a load of crap!",
            "expected": "rejected"
        },
        {
            "name": "Constructive criticism",
            "content": "The system has good potential but needs some improvements. The interface could be more user-friendly and some features are missing.",
            "expected": "approved"
        },
        {
            "name": "Highly positive",
            "content": "Absolutely fantastic! Best attendance system we've ever used. The team loves it and it has saved us countless hours. Exceptional service!",
            "expected": "approved"
        }
    ]
    
    print("=" * 80)
    print("TESTIMONIAL SENTIMENT ANALYSIS TEST")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print("-" * 80)
        print(f"Content: {test['content']}")
        
        analysis = TestimonialControl.analyze_testimonial_sentiment(test['content'])
        
        print(f"\nAnalysis Results:")
        print(f"  Is Appropriate: {analysis['is_appropriate']}")
        print(f"  Sentiment Score: {analysis['sentiment_score']:.3f}")
        print(f"  Sentiment Details: Pos={analysis['sentiment_details']['pos']:.2f}, "
              f"Neu={analysis['sentiment_details']['neu']:.2f}, "
              f"Neg={analysis['sentiment_details']['neg']:.2f}")
        print(f"  Contains Profanity: {analysis['contains_profanity']}")
        
        if analysis['profanity_found']:
            print(f"  Profanity Found: {', '.join(analysis['profanity_found'])}")
        
        if analysis['reason']:
            print(f"  Rejection Reason: {analysis['reason']}")
        
        # Determine if test passed
        would_be_status = "approved" if analysis['is_appropriate'] else "rejected"
        test_passed = (would_be_status == test['expected'])
        
        print(f"\n  Expected: {test['expected']}")
        print(f"  Would be: {would_be_status}")
        print(f"  Test Result: {'✓ PASS' if test_passed else '✗ FAIL'}")
        print("=" * 80)

if __name__ == "__main__":
    test_testimonial_sentiment()
