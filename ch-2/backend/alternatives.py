"""
Fallback methods for when AI services are unavailable
"""
import logging
import random

logger = logging.getLogger(__name__)

def get_rule_based_response(user_message):
    """Generate a simple rule-based response when AI services fail"""
    user_message = user_message.lower()
    
    # Greeting patterns
    if any(word in user_message for word in ['hello', 'hi', 'hey', 'greetings']):
        return "Hello! I'm currently operating in fallback mode. How can I help you?"
    
    # Questions about capabilities
    if any(word in user_message for word in ['can you', 'could you', 'able to']):
        return "I can help with information, answer questions, and have conversations, though I'm currently in fallback mode with limited capabilities."
    
    # Help request
    if any(word in user_message for word in ['help', 'assist', 'support']):
        return "I'm here to help, though I'm currently in fallback mode. Please ask a simple question and I'll do my best to assist."
    
    # Questions
    if any(word in user_message for word in ['what', 'who', 'when', 'where', 'why', 'how']):
        return "That's an interesting question. I'm currently in fallback mode with limited access to information. Could you ask something simpler or try again later?"
    
    # Farewells
    if any(word in user_message for word in ['bye', 'goodbye', 'see you', 'farewell']):
        return "Goodbye! Feel free to come back anytime."
    
    # Thanks
    if any(word in user_message for word in ['thanks', 'thank you', 'appreciate']):
        return "You're welcome! Is there anything else I can help with?"
    
    # Default responses
    default_responses = [
        "I'm currently operating in a limited capacity. Could you try a different question?",
        "I'm in fallback mode at the moment. Let's try a simpler conversation.",
        "I'm having trouble processing that request. Could you rephrase it?",
        "I understand you're trying to communicate with me, but I'm currently in fallback mode with limited capabilities.",
        "I'm operating with reduced functionality at the moment. Basic questions work best."
    ]
    
    return random.choice(default_responses)

def analyze_image_basic(format_name=None, width=None, height=None):
    """Generate a simple image analysis when AI services fail"""
    
    descriptions = [
        "I can see this is an image, but I can't analyze it in detail right now.",
        "This appears to be a photograph, but I can't process the specific details at the moment.",
        "I can tell you've shared an image, but I'm unable to analyze its contents in detail.",
        "I can confirm this is an image file, though I can't provide detailed analysis right now.",
        "I see you've uploaded an image, but I'm currently unable to process its specific contents."
    ]
    
    size_info = ""
    if width and height and format_name:
        size_info = f" It's a {format_name} file with dimensions {width}x{height}."
    
    return random.choice(descriptions) + size_info
