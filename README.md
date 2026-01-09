# SnowScrape Backend

Serverless Python backend for SnowScrape web scraping platform, deployed on AWS Lambda using the Serverless Framework.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Setup](#setup)
- [Deployment](#deployment)
- [Lambda Functions](#lambda-functions)
- [Environment Variables](#environment-variables)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

The backend provides:
- REST API for job management (CRUD operations)
- Scheduled job execution via CloudWatch Events
- Asynchronous job processing via SQS
- Web scraping with XPath, Regex, and JSONPath support
- Result storage in AWS S3
- Metrics integration with Snowglobe

---

## Architecture

### Components

- **handler.py** - Lambda function handlers for API endpoints
- **job_manager.py** - Business logic for job CRUD operations
- **crawl_manager.py** - Orchestrates crawling process
- **crawler.py** - Core web scraping logic
- **utils.py** - File parsing, URL extraction, and utilities
- **snowglobe.py** - Metrics client for monitoring

### AWS Services Used

- **API Gateway** - REST API with JWT authentication
- **Lambda** - Serverless function execution
- **DynamoDB** - Job metadata and URL tracking
- **S3** - Result file storage
- **SQS** - Message queue for async processing
- **CloudWatch** - Logging and scheduled events

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 20+ (for Serverless Framework)
- AWS CLI configured with credentials
- AWS Account with appropriate permissions

### 1. Install Dependencies

```bash
cd backend

# Install Node.js dependencies (Serverless Framework and plugins)
npm install

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

```bash
aws configure

# You'll be prompted for:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-2)
# - Default output format (json)
```

### 3. Update Configuration

Edit `serverless.yml` to configure:
- AWS region (default: us-east-2)
- DynamoDB table names
- S3 bucket name
- SQS queue name
- Environment-specific settings (dev/prod)

**Important:** Remove hardcoded secrets from `serverless.yml` before production deployment (Phase 11).

---

## Deployment

### Deploy to Development

```bash
# Deploy all functions and resources
npx serverless deploy --stage dev

# Output will show:
# - API Gateway endpoint URL
# - Lambda function names
# - DynamoDB table names
# - S3 bucket name
```

### Deploy Individual Function

```bash
# Faster deployment for code-only changes
npx serverless deploy function --function create_job --stage dev
```

### Deploy to Production

```bash
npx serverless deploy --stage prod
```

### View Logs

```bash
# Tail logs for a specific function
npx serverless logs --function create_job --stage dev --tail

# View recent logs
npx serverless logs --function job_processor --stage dev
```

### Remove Deployment

```bash
# WARNING: This will delete all resources including data!
npx serverless remove --stage dev
```

---

## Lambda Functions

### API Handlers

#### POST /jobs - Create Job
**Handler:** `handler.create_job`
**Description:** Create a new scraping job
**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "jobName": "string",
  "fileSource": "string (URL or SFTP path)",
  "fileMapping": {
    "delimiter": "string",
    "enclosure": "string",
    "escape": "string",
    "urlColumns": [0, 1]
  },
  "queries": [
    {
      "queryType": "xpath|regex|jsonpath",
      "selector": "string",
      "resultName": "string"
    }
  ],
  "schedule": {
    "days": 0,
    "hours": 0,
    "minutes": 30
  },
  "concurrency": 3
}
```

**Response:**
```json
{
  "jobId": "uuid-string"
}
```

#### GET /jobs - List Jobs
**Handler:** `handler.get_jobs`
**Description:** Get all jobs for authenticated user
**Authentication:** Required (JWT)

**Response:**
```json
{
  "jobs": [
    {
      "jobId": "string",
      "jobName": "string",
      "status": "active|paused|completed|failed",
      "lastRun": 1234567890,
      "nextRun": 1234567890,
      ...
    }
  ]
}
```

#### GET /jobs/{jobId} - Get Job
**Handler:** `handler.get_job`
**Description:** Get specific job details
**Authentication:** Required (JWT)

#### PUT /jobs/{jobId} - Update Job
**Handler:** `handler.update_job`
**Description:** Update job configuration
**Authentication:** Required (JWT)

#### DELETE /jobs/{jobId} - Delete Job
**Handler:** `handler.delete_job`
**Description:** Delete a job
**Authentication:** Required (JWT)

#### POST /jobs/{jobId}/pause - Pause/Resume Job
**Handler:** `handler.pause_job`
**Description:** Toggle job active/paused status
**Authentication:** Required (JWT)

#### POST /jobs/{jobId}/refresh - Refresh Job
**Handler:** `handler.refresh_job`
**Description:** Re-crawl all URLs for a job
**Authentication:** Required (JWT)

#### GET /health - Health Check
**Handler:** `handler.health_check`
**Description:** Health status endpoint
**Authentication:** Not required

### Background Processors

#### job_processor
**Handler:** `handler.job_processor`
**Trigger:** SQS Queue
**Description:** Process scraping jobs asynchronously
**Batch Size:** 5 messages

**Process:**
1. Receive job message from SQS
2. Fetch and parse CSV file
3. Extract URLs from specified columns
4. Crawl URLs with configured queries
5. Store results in S3
6. Update job status in DynamoDB
7. Delete SQS message

#### scheduler
**Handler:** `handler.scheduler`
**Trigger:** CloudWatch Event (rate: 1 minute)
**Description:** Schedule jobs for execution

**Process:**
1. Scan DynamoDB for jobs due to run
2. For each job:
   - Check if `nextRun <= now()`
   - Check if `status == 'active'`
   - Enqueue job message to SQS
   - Update `lastRun` and `nextRun`

---

## Environment Variables

### Lambda Environment Variables

Configured in `serverless.yml`:

| Variable | Description | Example |
|----------|-------------|---------|
| `DYNAMODB_TABLE` | Jobs table name | `snowscrape-jobs-dev` |
| `DYNAMODB_URL_TABLE` | URLs table name | `snowscrape-urls-dev` |
| `S3_BUCKET` | Results bucket | `snowscrape-results` |
| `SQS_QUEUE_URL` | SQS queue URL | `https://sqs.us-east-2.amazonaws.com/...` |
| `CLERK_JWT_PUBLIC_KEY` | Clerk JWT public key | See serverless.yml |
| `CLERK_JWT_SECRET_KEY` | Clerk secret key | See serverless.yml |

### Local Development

Create `.env` file for local testing:

```bash
DYNAMODB_TABLE=snowscrape-jobs-dev
DYNAMODB_URL_TABLE=snowscrape-urls-dev
S3_BUCKET=snowscrape-results
SQS_QUEUE_URL=https://sqs.us-east-2.amazonaws.com/xxx/SnowscrapeJobQueue
AWS_REGION=us-east-2
```

---

## Development

### Project Structure

```
backend/
├── handler.py              # Lambda entry points
├── job_manager.py          # Job CRUD logic
├── crawl_manager.py        # Crawl orchestration
├── crawler.py              # Web scraping engine
├── utils.py                # Utilities (parsing, extraction)
├── snowglobe.py            # Metrics client
├── serverless.yml          # Serverless Framework config
├── requirements.txt        # Python dependencies
├── package.json            # Node.js dependencies
└── README.md              # This file
```

### Code Style

- Follow PEP 8 style guide
- Use type hints where appropriate
- Document functions with docstrings
- Keep functions focused and small

### Adding a New Lambda Function

1. Add handler function to `handler.py`:
```python
def my_new_function(event, context):
    # Your code here
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Success'})
    }
```

2. Add function definition to `serverless.yml`:
```yaml
functions:
  myNewFunction:
    handler: handler.my_new_function
    events:
      - http:
          path: /my-endpoint
          method: get
          cors: true
```

3. Deploy:
```bash
npx serverless deploy function --function myNewFunction --stage dev
```

### Local Invocation

```bash
# Invoke function locally
npx serverless invoke local --function create_job --path test/create_job_event.json

# Create test event file (test/create_job_event.json):
{
  "body": "{\"jobName\": \"Test Job\"}",
  "headers": {
    "Authorization": "Bearer test-token"
  }
}
```

---

## Testing

### Unit Tests (Phase 3)

**Coming soon:** Comprehensive test suite using pytest.

```bash
# Install test dependencies
pip install pytest pytest-cov moto pytest-mock

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Integration Tests (Phase 3)

**Coming soon:** Integration tests with LocalStack for AWS services.

### Manual Testing

Use tools like Postman or curl to test API endpoints:

```bash
# Health check
curl https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/health

# Create job (requires JWT token)
curl -X POST https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/jobs \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_job.json

# List jobs
curl https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/jobs \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Troubleshooting

### Common Issues

#### 1. Deployment Fails with "Access Denied"

**Cause:** Insufficient IAM permissions

**Solution:**
- Ensure AWS credentials have permissions for:
  - Lambda (CreateFunction, UpdateFunctionCode)
  - API Gateway (CreateRestApi, CreateDeployment)
  - DynamoDB (CreateTable, DescribeTable)
  - S3 (CreateBucket, PutObject)
  - CloudWatch (PutRule, CreateLogGroup)
  - IAM (CreateRole, AttachRolePolicy)

#### 2. Function Times Out

**Cause:** Function execution exceeds timeout limit

**Solution:**
- Increase timeout in `serverless.yml`:
```yaml
functions:
  myFunction:
    handler: handler.my_function
    timeout: 300  # 5 minutes (max: 900 seconds)
```

#### 3. "Module not found" Error

**Cause:** Missing Python dependencies

**Solution:**
```bash
# Ensure dependencies are installed in virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# If deploying, ensure serverless-python-requirements plugin is installed
npm install
```

#### 4. DynamoDB Throttling

**Cause:** Exceeding provisioned capacity

**Solution:**
- Enable auto-scaling in `serverless.yml`
- Or switch to on-demand billing mode

#### 5. Cold Start Latency

**Cause:** Lambda cold starts

**Solution (Phase 6):**
- Optimize package size
- Use provisioned concurrency for critical functions
- Implement connection pooling

### Viewing Logs

```bash
# CloudWatch Logs
aws logs tail /aws/lambda/snowscrape-dev-create_job --follow

# Or use Serverless Framework
npx serverless logs --function create_job --stage dev --tail
```

### Debugging

Add logging throughout your code:

```python
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def my_function(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    # Your code
    logger.error(f"Error occurred: {str(e)}")
```

---

## Performance Optimization (Phase 6)

### Planned Improvements

1. **Connection Pooling**
   - Reuse DynamoDB connections across invocations
   - HTTP connection pooling for web requests

2. **Batch Operations**
   - Batch DynamoDB writes for URL state
   - Batch SQS message sends

3. **Query Instead of Scan**
   - Add GSI on `nextRun` + `status`
   - Replace scan in scheduler with query

4. **Concurrent Crawling**
   - Process multiple URLs in parallel
   - Respect job's concurrency setting

5. **Lambda Optimization**
   - Reduce deployment package size
   - Move imports inside functions (if beneficial)
   - Consider Lambda Layers for dependencies

---

## Security Notes (Phase 11)

### Current Security Issues

⚠️ **WARNING:** The following security issues must be addressed before production:

1. **Hardcoded Secrets** (serverless.yml:270-283)
   - Clerk JWT keys exposed in config
   - Move to AWS Secrets Manager

2. **Overly Permissive IAM**
   - IAM policies use wildcards (`dynamodb:*`, `s3:*`)
   - Implement least-privilege policies

3. **No Rate Limiting**
   - API endpoints lack throttling
   - Add API Gateway usage plans

4. **No Input Validation**
   - Missing validation for XPath/Regex queries
   - Risk of injection attacks

See **[IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) Phase 11** for security hardening roadmap.

---

## Monitoring & Metrics

### CloudWatch Metrics

Key metrics to monitor:
- Lambda invocations, errors, duration
- DynamoDB read/write capacity
- SQS message count, age
- API Gateway 4xx/5xx errors

### Snowglobe Integration

The backend sends custom metrics to Snowglobe:
- `job_created`
- `job_updated`
- `job_deleted`
- `job_started`
- `job_completed`
- `job_failed`

### Alarms (Phase 7)

**Coming soon:** CloudWatch alarms for:
- Lambda error rate > 5%
- DynamoDB throttling
- SQS DLQ messages > 0
- API Gateway latency > 3s

---

## API Documentation

For detailed API schema and examples, see:
- [ARCHITECTURE.md](../ARCHITECTURE.md) - API endpoints section
- OpenAPI/Swagger spec (coming in Phase 10)

---

## Support

- See [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) for development roadmap
- Check [ARCHITECTURE.md](../ARCHITECTURE.md) for system design
- Review CloudWatch logs for runtime errors

---

**Last Updated:** January 8, 2026
