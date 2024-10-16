import json
import boto3
import os
import urllib3
import redis
from botocore.exceptions import ClientError
from datetime import timedelta

# Initialize the Redis client for ElastiCache
redis_host = os.getenv('REDIS_HOST')  # Redis ElastiCache endpoint
redis_port = 6379  # Default Redis port

# Create a Redis connection
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, ssl=True, ssl_cert_reqs="none", decode_responses=True)

# Initialize the Bedrock client with the correct region (us-east-1 in this case)
bedrock = boto3.client(service_name='bedrock-agent-runtime', region_name='us-east-1')

# Slack-related setup: Slack URL and token should be set as environment variables
slack_url = 'https://slack.com/api/chat.postMessage'
slack_token = os.environ.get('SLACK_TOKEN')  # Set this in the Lambda environment variables

http = urllib3.PoolManager()

def event_id_already_processed(event_id):
    """
    Checks if the Slack event_id already exists in Redis.
    Returns True if the event has already been processed, False otherwise.
    """
    return redis_client.exists(event_id)  # Returns 1 if the key exists, otherwise 0

def mark_event_as_processed(event_id):
    """
    Marks the Slack event_id as processed by inserting it into Redis with an expiry time.
    The event_id will be stored with a TTL (time-to-live) to limit how long it is cached.
    """
    try:
        # Store the event ID in Redis with a TTL of 1 hour (3600 seconds)
        redis_client.setex(event_id, timedelta(hours=1), 'processed')
    except Exception as e:
        print(f"Error storing event {event_id} in Redis: {str(e)}")
        raise

def call_bedrock_agent(question, agent_id, request_id):
    """
    Invokes the AWS Bedrock agent (knowledge base) with the provided question using 'invoke_agent'.
    Follows the full request syntax as per the documentation.
    """

    # Optional parameters
    agent_alias_id = os.environ.get('AGENT_ID_ALIAS')
    enable_trace = True
    end_session = False
    session_id = request_id
    
    try:
        # Invoke the Bedrock agent (full syntax)
        response = bedrock.invoke_agent(
            agentAliasId=agent_alias_id,
            agentId=agent_id,
            enableTrace=enable_trace,
            endSession=end_session,
            inputText=question,
            sessionId=session_id
        )

        completion = ""
        for event in response.get("completion"):
            chunk = event.get("chunk", None)  # Use .get() to prevent KeyError
            print('chunk: ', chunk)
            if chunk:
                decoded_bytes = chunk.get("bytes").decode()
                print('bytes: ', decoded_bytes)
                if decoded_bytes.strip():
                    completion = completion + decoded_bytes

    except Exception as e:
        print(json.dumps({'error': str(e)}))
        print(f"Couldn't invoke agent. {e}")
        raise

    # Process the response from the agent
    print(f'response ({request_id}): {response}')
    print(f'completion ({request_id}): {completion}')
    if completion:
        return completion  # Assuming the response contains the 'message'
    else:
        return 'No response from the agent.'


def send_message_to_slack(channel, message, user_id, thread_ts):
    """
    Sends a message to a Slack channel.
    """
    data = {
        'channel': channel,
        'text': f"<@{user_id}> {message}",  # Tag the user who triggered the message
        'thread_ts': thread_ts,
    }

    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }

    # Send the message to the Slack API
    response = http.request('POST', slack_url, headers=headers, body=json.dumps(data))
    
    # Log response for debugging purposes
    print(f'Slack response: {response.status}, {response.data}')


def lambda_handler(event, context):
    """
    Main handler function for AWS Lambda. It processes the incoming event (e.g., from Slack),
    invokes the Bedrock agent, and sends a response back to Slack.
    """
    body_obj = json.loads(event.get('body'))
    event_id = body_obj['event_id']
    print(f"Received event ({event_id}): {json.dumps(event)}")
    
    if not event_id_already_processed(event_id):
        # Get the AWS Request ID from the event context
        request_id = context.aws_request_id
        # Parse the Slack event data
        #slack_body = json.loads(event['body'])
        slack_text = body_obj.get('event').get('text')  # Text from the Slack message
        slack_user = body_obj.get('event').get('user')  # User who sent the message
        channel = body_obj.get('event').get('channel')  # Slack channel ID
        thread_ts = body_obj.get('event').get('ts') # threa id
        # Replace the bot's Slack user ID from the message
        slack_bot_user_id = os.environ.get('SLACK_BOT_USER_ID')

        # Add a condition to stop if the bot is messaging itself
        if slack_user == slack_bot_user_id:
            print("Bot is messaging itself. Stopping execution.")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Bot ignored its own message'})
            }

        cleaned_question = slack_text.replace(f'<@{slack_bot_user_id}>', '').strip()
        # Call the Bedrock agent using the provided question (cleaned)
        agent_id = os.environ.get('AGENT_ID')
        try:
            assistant_response = call_bedrock_agent(cleaned_question, agent_id, request_id)
            # Send the assistant's response back to Slack
            send_message_to_slack(channel, assistant_response, slack_user, thread_ts)
            # Mark the event as processed to prevent duplicate handling
            mark_event_as_processed(event_id)
        except Exception as e:
            err = f"Uh-oh! Something went wrong. Please try again in a few minutes or reach out to our support team if the issue persists. (Error: {e})"
            send_message_to_slack(channel, err, slack_user, thread_ts)
    else:
        print(f"Event {event_id} already processed.")

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Success'})
    }