#!/usr/bin/env python3
"""
Local test script for the prayer journal Lambda function.
Simulates API Gateway events without requiring actual AWS credentials.
"""

import json
import sys
import os
from unittest.mock import patch, MagicMock

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the lambda function
from lambda_function import lambda_handler

def create_event(http_method="GET", path="events", body=None, query_params=None):
    """Create a mock API Gateway event."""
    event = {
        'httpMethod': http_method,
        'path': path,
        'body': json.dumps(body) if body else None,
        'isBase64Encoded': False
    }
    if query_params:
        event['queryStringParameters'] = query_params
    return event

def test_get_events():
    """Test GET /events endpoint."""
    print("=== Test GET /events ===")
    event = create_event(http_method="GET", path="events")
    
    # Mock the calendar service to avoid actual API calls
    with patch('lambda_function.calendar_service') as mock_service:
        # Mock events list result
        mock_events_result = MagicMock()
        mock_events_result.get.return_value = {
            'items': [
                {
                    'id': 'test_event_1',
                    'summary': 'Test Event 1',
                    'start': {'dateTime': '2024-01-15T09:00:00Z'}
                },
                {
                    'id': 'test_event_2', 
                    'summary': 'Test Event 2',
                    'start': {'dateTime': '2024-01-15T14:30:00Z'}
                }
            ]
        }
        mock_service.events().list.return_value.execute.return_value = mock_events_result
        
        # Also mock the Google service initialization
        with patch('lambda_function.get_google_service') as mock_init:
            mock_init.return_value = mock_service
            
            result = lambda_handler(event, {})
            print(f"Status Code: {result['statusCode']}")
            print(f"Body: {result['body'][:100]}...")
            
            # Parse body
            body = json.loads(result['body'])
            assert body['success'] == True, "Expected success=True"
            assert body['count'] == 2, f"Expected count=2, got {body['count']}"
            print("✓ Test passed!\n")

def test_get_motivations():
    """Test GET /motivations endpoint."""
    print("=== Test GET /motivations ===")
    event = create_event(http_method="GET", path="motivations")
    
    # Mock S3 get_object
    with patch('lambda_function.get_s3_client') as mock_s3_client:
        mock_response = {
            'Body': MagicMock()
        }
        mock_response['Body'].read.return_value = "Pace\nGrazie\nSerenità"
        mock_s3_client.return_value.get_object.return_value = mock_response
        
        # Also mock list_objects for bucket existence check
        mock_s3_client.return_value.head_bucket.return_value = {}
        
        result = lambda_handler(event, {})
        print(f"Status Code: {result['statusCode']}")
        print(f"Body (first 80 chars): {result['body'][:80]}...")
        
        body = result['body']
        assert 'Pace' in body, "Expected motivations text"
        print("✓ Test passed!\n")

def test_post_update_motivi():
    """Test POST /update-motivi endpoint."""
    print("=== Test POST /update-motivi ===")
    event = create_event(
        http_method="POST", 
        path="update-motivi",
        body={'motivi': 'Nuovo motivo di preghiera\nSecondo motivo'}
    )
    
    # Mock S3 put_object
    with patch('lambda_function.get_s3_client') as mock_s3_client:
        mock_s3_client.return_value.put_object.return_value = {}
        mock_s3_client.return_value.head_bucket.return_value = {}
        
        result = lambda_handler(event, {})
        print(f"Status Code: {result['statusCode']}")
        print(f"Body: {result['body']}")
        
        body = json.loads(result['body'])
        assert body['success'] == True, f"Expected success=True, got {body}"
        print("✓ Test passed!\n")

def test_cors_preflight():
    """Test OPTIONS/CORS preflight."""
    print("=== Test OPTIONS (CORS) ===")
    event = create_event(http_method="OPTIONS", path="events")
    
    result = lambda_handler(event, {})
    print(f"Status Code: {result['statusCode']}")
    headers = result.get('headers', {})
    assert headers.get('Access-Control-Allow-Origin') == '*', "Expected CORS header"
    print("✓ Test passed!\n")

def test_not_found():
    """Test unknown endpoint."""
    print("=== Test Unknown Endpoint ===")
    event = create_event(http_method="GET", path="unknown")
    
    result = lambda_handler(event, {})
    print(f"Status Code: {result['statusCode']}")
    body = json.loads(result['body'])
    assert body['error'] == 'Not found', f"Expected Not found error"
    print("✓ Test passed!\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Prayer Journal Lambda - Local Tests")
    print("="*60 + "\n")
    
    tests = [
        test_get_events,
        test_get_motivations, 
        test_post_update_motivi,
        test_cors_preflight,
        test_not_found,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("="*60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*60 + "\n")
    
    sys.exit(0 if failed == 0 else 1)