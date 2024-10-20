# AWS Lambda Event Processing with Slack Notifications and Bedrock Integration

This AWS Lambda function integrates Slack messaging and AWS services, including AWS Bedrock, to handle incoming events, send notifications to Slack, and ensure event idempotency using Redis. You can either use **AWS ElastiCache** or your own Redis instance for managing event IDs. This solution is tailored for event-driven workflows within the AWS Bedrock models platform.

## Features

- **Redis (ElastiCache) or Custom Redis Integration**: Used to track and store event IDs to ensure that each event is processed only once. You can connect either to AWS ElastiCache or your own Redis instance.
- **Slack Notifications**: Posts messages to Slack channels using the Slack API.
- **AWS Bedrock Client**: Integrated to interact with Bedrock runtime (region `us-east-1`), specifically for handling tasks related to Bedrock models.
- **Environment Variables**: Configurable via a `.env` file to securely store sensitive data like Redis host, Slack token, and AWS region.

## Environment Variables

The function relies on the following environment variables, which are provided in the `.env.example` file. You should rename this file to `.env` and replace the placeholder values with your actual configuration:

- `AGENT_ID`: The agent ID used for Bedrock interaction.
- `AGENT_ID_ALIAS`: The alias for the agent ID.
- `KB_ID`: The knowledge base ID associated with Bedrock.
- `MODEL_ID`: The ID of the specific model used (e.g., `anthropic.claude-3-5-sonnet-20240620-v1:0`).
- `REDIS_HOST`: The host URL for either the Redis ElastiCache instance or your custom Redis instance.
- `SLACK_BOT_USER_ID`: The user ID of the Slack bot used for messaging.
- `SLACK_TOKEN`: The token for authenticating requests to the Slack API.
- `AWS_REGION`: AWS region to initialize the Bedrock client (default is `us-east-1`).

Make sure to rename `.env.example` to `.env` and update the values with your environment-specific configuration.

## Setup

1. **Rename the `.env.example` file** to `.env` and replace the placeholders with real values for `AGENT_ID`, `AGENT_ID_ALIAS`, `KB_ID`, `MODEL_ID`, `REDIS_HOST`, `SLACK_BOT_USER_ID`, `SLACK_TOKEN`, and other required variables.
2. Deploy the Lambda function to your AWS account.
3. Ensure that the Lambda configuration is set up with the correct environment variables (`REDIS_HOST`, `SLACK_TOKEN`, etc.).
4. Grant the Lambda function appropriate IAM permissions to access Redis, Slack, and AWS Bedrock services.

## Redis Setup

- The function connects to Redis over SSL (`redis.StrictRedis`) and assumes Redis is accessible via the `REDIS_HOST` endpoint, which can either be an AWS ElastiCache instance or your own Redis setup.

## Slack Integration

- The function sends messages to Slack using the `https://slack.com/api/chat.postMessage` endpoint.
- The Slack token must be provided via the `SLACK_TOKEN` environment variable in the `.env` file.

## Dependencies

- `boto3`: AWS SDK for Python.
- `redis`: Redis Python client for interacting with ElastiCache or custom Redis instances.
- `urllib3`: For HTTP communication with the Slack API.

## Lambda Handler

The entry point for this function is the `lambda_handler(event, context)` function. It processes incoming events, checks Redis for duplicate event IDs, and sends notifications to Slack if the event is new.
