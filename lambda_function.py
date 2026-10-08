import os
import json
import boto3
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration from Environment Variables ---
SERVICE_ACCOUNT_PATH = os.environ.get("SERVICE_ACCOUNT_JSON", "/opt/service_account.json")
MEDEA_CALENDAR_ID = os.environ.get("MEDEA_CALENDAR_ID", "medealfonso1103@gmail.com")
NOTE_ID = os.environ.get("NOTE_ID", "15vvB-6erRQOGzkLtTkQyzZCSAGPcVJ1QU2gfa7CxpWjavMHfZ8JtjHsGCvPT5JDGPk7Usw")
MOTIVATIONS_BUCKET = os.environ.get("MOTIVATIONS_BUCKET", "prayer-journal-motivations")
MOTIVATIONS_KEY = os.environ.get("MOTIVATIONS_KEY", "motivi.txt")

# --- Initialize Google Services ---
def get_google_service(service_name, version='v3'):
    """Initialize and return Google service object."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_PATH,
            scopes=[
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/keep"
            ]
        )
        return build(service_name, version, credentials=credentials)
    except Exception as e:
        print(f"Error initializing Google {service_name} service: {e}")
        raise

# Initialize services (will be reused across invocations)
try:
    calendar_service = get_google_service('calendar')
    keep_service = get_google_service('keep')
except Exception as e:
    print(f"Warning: Could not initialize Google services: {e}")
    calendar_service = None
    keep_service = None

# --- S3 Helper Functions ---
def get_s3_client():
    """Get S3 client."""
    return boto3.client('s3')

def load_motivations_from_s3():
    """Load motivations from S3 bucket."""
    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=MOTIVATIONS_BUCKET, Key=MOTIVATIONS_KEY)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error loading motivations from S3: {e}")
        # Return default motivations
        return "Pace per la famiglia\nGrazie per la giornata\nSalute e serenità"

def save_motivations_to_s3(content):
    """Save motivations to S3 bucket."""
    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket=MOTIVATIONS_BUCKET,
            Key=MOTIVATIONS_KEY,
            Body=content.encode('utf-8'),
            ContentType='text/plain'
        )
        return True
    except Exception as e:
        print(f"Error saving motivations to S3: {e}")
        return False

# --- Calendar Functions ---
def fetch_calendar_events():
    """Fetch today's events from Google Calendar."""
    if not calendar_service:
        return []
    
    try:
        now = datetime.utcnow()
        # Start of today (00:00:00)
        time_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        # Start of tomorrow
        time_max = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        
        events = []
        # Check both calendars
        for cal_id, name in [("luca.buccheri.92@gmail.com", "Luca"), (MEDEA_CALENDAR_ID, "Medea")]:
            try:
                events_result = calendar_service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=10,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                for item in events_result.get('items', []):
                    start = item['start'].get('dateTime', item['start'].get('date'))
                    # Extract time part if available
                    time_str = ''
                    if 'T' in start:
                        time_str = start.split('T')[1][:5]  # HH:MM
                    
                    events.append({
                        'id': item['id'],
                        'title': f"[{name}] {item.get('summary', 'Evento senza titolo')}",
                        'done': False,  # Not persisting completion status
                        'time': time_str,
                    })
            except HttpError as error:
                print(f"Error fetching events for calendar {cal_id}: {error}")
                continue
        
        return events[:5]  # Return max 5 events
    except Exception as e:
        print(f"Error in fetch_calendar_events: {e}")
        return []

# --- Keep/Notes Functions ---
def fetch_keep_note():
    """Fetch the prayer note from Google Keep."""
    if not keep_service:
        return "Nota non disponibile"
    
    try:
        note = keep_service.notes().get(name=f"notes/{NOTE_ID}").execute()
        # Extract text content
        text_parts = []
        body = note.get('body', {})
        
        if 'text' in body:
            text_parts.append(body['text'].get('text', ''))
        if 'list' in body:
            for item in body['list'].get('listItems', []):
                item_text = item.get('text', {}).get('text', '')
                if item_text:
                    text_parts.append('• ' + item_text)
        
        note_text = '\n'.join(p for p in text_parts if p)
        return note_text if note_text.strip() else note.get('title', 'Nota preghiera')
    except Exception as e:
        print(f"Error fetching Keep note: {e}")
        return "Nota non accessibile"

# --- Lambda Handler ---
def lambda_handler(event, context):
    """
    AWS Lambda handler for API Gateway.
    Supports:
    - GET /events - Get today's calendar events
    - GET /motivations - Get motivations from S3
    - POST /update-motivi - Update motivations in S3
    - GET /keep-note - Get prayer note from Google Keep
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Extract HTTP method and path
    http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'GET'))
    path = event.get('path', event.get('rawPath', '/'))
    
    # Normalize path
    if path.startswith('/'):
        path = path[1:]  # Remove leading slash
    
    # Route handling
    try:
        if http_method == 'GET':
            if path == 'events':
                events = fetch_calendar_events()
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                    },
                    'body': json.dumps({
                        'success': True,
                        'data': events,
                        'count': len(events)
                    })
                }
            elif path == 'motivations':
                motivations = load_motivations_from_s3()
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'text/plain',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                    },
                    'body': motivations
                }
            elif path == 'keep-note':
                note_text = fetch_keep_note()
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'text/plain',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                    },
                    'body': json.dumps({
                        'success': True,
                        'data': note_text
                    })
                }
            else:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'success': False, 'error': 'Not found'})
                }
        
        elif http_method == 'POST':
            if path == 'update-motivi':
                # Parse body
                body = event.get('body', '{}')
                if isinstance(body, str):
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError:
                        payload = {}
                else:
                    payload = body
                
                motivi_text = payload.get('motivi', '')
                if not motivos_text:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({'success': False, 'error': 'Missing motivi parameter'})
                    }
                
                success = save_motivations_to_s3(motivi_text)
                return {
                    'statusCode': 200 if success else 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                    },
                    'body': json.dumps({'success': success})
                }
            else:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'success': False, 'error': 'Not found'})
                }
        
        elif http_method == 'OPTIONS':
            # Handle CORS preflight
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': ''
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'error': 'Method not allowed'})
            }
    
    except Exception as e:
        print(f"Unhandled error in lambda_handler: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': False, 'error': 'Internal server error'})
        }