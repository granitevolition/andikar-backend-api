"""
Utility functions for the Andikar API Backend
"""
import httpx
import logging
import random
import re
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("andikar-backend-utils")

async def call_humanizer_api(text: str, api_url: str) -> Tuple[str, bool]:
    """
    Call the external humanizer API to transform text
    
    Args:
        text: The text to humanize
        api_url: The base URL of the humanizer API
        
    Returns:
        Tuple of (result, success)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/humanize_text",
                json={"input_text": text},
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Humanizer API returned error: {response.status_code} - {response.text}")
                return text, False
                
            data = response.json()
            return data.get("result", text), True
            
    except Exception as e:
        logger.error(f"Error calling humanizer API: {str(e)}")
        return text, False

def detect_ai_content(text: str) -> Dict[str, Any]:
    """
    Simple AI content detection algorithm
    This is a fallback for when the external AI detection service is unavailable
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary with detection results
    """
    # Detection heuristics - looking for patterns common in AI text
    ai_indicators = [
        "furthermore,", "additionally,", "moreover,", "thus,", "therefore,",
        "consequently,", "hence,", "as a result,", "in conclusion,",
        "to summarize,", "in summary,", "in essence,"
    ]

    # Count indicators
    indicator_count = sum(text.lower().count(indicator) for indicator in ai_indicators)

    # Check for repetitive phrases
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentence_starts = [sentence.split()[0].lower() if sentence.split() else "" for sentence in sentences]
    repeated_starts = len(sentence_starts) - len(set(sentence_starts))

    # Calculate uniformity of sentence length (standard deviation as percentage of mean)
    sentence_lengths = [len(sentence) for sentence in sentences if sentence]
    if sentence_lengths:
        mean_length = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((length - mean_length) ** 2 for length in sentence_lengths) / len(sentence_lengths)
        std_dev = variance ** 0.5
        length_uniformity = std_dev / mean_length if mean_length > 0 else 0
    else:
        length_uniformity = 0

    # Calculate AI likelihood score (0-100)
    base_score = min(100, (indicator_count * 10) + (repeated_starts * 5) + (100 - length_uniformity * 100))
    randomizer = random.uniform(0.85, 1.15)  # Add some randomness
    ai_score = min(100, max(0, base_score * randomizer))

    # Results
    result = {
        "ai_score": round(ai_score, 1),
        "human_score": round(100 - ai_score, 1),
        "analysis": {
            "formal_language": min(100, indicator_count * 15),
            "repetitive_patterns": min(100, repeated_starts * 20),
            "sentence_uniformity": min(100, (1 - length_uniformity) * 100)
        }
    }

    return result

async def initiate_mpesa_payment(
    phone_number: str, 
    amount: float, 
    account_reference: str,
    transaction_desc: str,
    consumer_key: str,
    consumer_secret: str,
    passkey: str,
    shortcode: str,
    callback_url: str
) -> Dict[str, Any]:
    """
    Initiate an M-Pesa STK push payment
    
    This is a simplified implementation. A real implementation would need to:
    - Generate the correct timestamp format
    - Create and encode the password properly
    - Handle token generation and authentication
    - Process the response correctly
    
    Args:
        phone_number: The customer's phone number (format: 254XXXXXXXXX)
        amount: The amount to charge
        account_reference: Reference for the transaction
        transaction_desc: Description of the transaction
        consumer_key: M-Pesa API consumer key
        consumer_secret: M-Pesa API consumer secret
        passkey: M-Pesa API passkey
        shortcode: M-Pesa shortcode
        callback_url: URL to receive payment notification
        
    Returns:
        Dictionary with the M-Pesa API response
    """
    if not all([consumer_key, consumer_secret, passkey, shortcode, callback_url]):
        # Simulate successful response for testing
        return {
            "checkout_request_id": f"ws_CO_{random.randint(100000, 999999)}",
            "response_code": "0",
            "response_description": "Success (Simulated)",
            "customer_message": "Success. Request accepted for processing"
        }
    
    try:
        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Create password (Simplified - real implementation uses specific format)
        password = f"{shortcode}{passkey}{timestamp}"
        import base64
        password = base64.b64encode(password.encode()).decode('utf-8')
        
        # Get access token (Simplified)
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
                auth=(consumer_key, consumer_secret)
            )
            auth_data = auth_response.json()
            token = auth_data.get("access_token")
            
            if not token:
                logger.error(f"Failed to get M-Pesa access token: {auth_data}")
                return {
                    "error": "Authentication failed",
                    "detail": "Could not retrieve M-Pesa access token"
                }
                
            # Format phone number (remove leading 0 if present)
            if phone_number.startswith("0"):
                phone_number = "254" + phone_number[1:]
            elif not phone_number.startswith("254"):
                phone_number = "254" + phone_number
                
            # Prepare request payload
            payload = {
                "BusinessShortCode": shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": str(int(amount)),
                "PartyA": phone_number,
                "PartyB": shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": callback_url,
                "AccountReference": account_reference,
                "TransactionDesc": transaction_desc
            }
            
            # Make STK Push request
            response = await client.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                logger.error(f"M-Pesa API error: {response.status_code} - {response.text}")
                return {
                    "error": "Payment initiation failed",
                    "detail": response.text
                }
                
            data = response.json()
            
            # Format response
            return {
                "checkout_request_id": data.get("CheckoutRequestID"),
                "response_code": data.get("ResponseCode"),
                "response_description": data.get("ResponseDescription"),
                "customer_message": data.get("CustomerMessage")
            }
                
    except Exception as e:
        logger.error(f"Error in M-Pesa payment processing: {str(e)}")
        return {
            "error": "Payment processing error",
            "detail": str(e)
        }

async def query_transaction_status(
    checkout_request_id: str,
    consumer_key: str,
    consumer_secret: str,
    passkey: str,
    shortcode: str
) -> Dict[str, Any]:
    """
    Query the status of an M-Pesa transaction
    
    Args:
        checkout_request_id: The checkout request ID
        consumer_key: M-Pesa API consumer key
        consumer_secret: M-Pesa API consumer secret
        passkey: M-Pesa API passkey
        shortcode: M-Pesa shortcode
        
    Returns:
        Dictionary with the transaction status
    """
    # Similar implementation to initiate_mpesa_payment
    # Would query the M-Pesa API for transaction status
    
    # For demo purposes, return a simulated response
    return {
        "result_code": "0",
        "result_desc": "The service request has been accepted successfully",
        "checkout_request_id": checkout_request_id,
        "amount": random.randint(10, 1000),
        "mpesa_receipt_number": f"LHG{random.randint(100000, 999999)}XYZ",
        "transaction_date": datetime.now().strftime('%Y%m%d%H%M%S'),
        "phone_number": f"254{random.randint(700000000, 799999999)}"
    }