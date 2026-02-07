# Observatory Integration

Snowscrape integrates with the [Snowglobe Observatory](https://snowglobe.alexdiaz.me/observatory) for centralized monitoring and health tracking across your application ecosystem.

## Overview

The Observatory provides:
- **Centralized Health Monitoring** - Track uptime and service availability
- **Business Metrics** - Monitor job success rates, crawl performance, and KPIs
- **Cross-App Visibility** - Compare snowscrape performance with other services
- **Unified Alerting** - Get notified when metrics deviate from expected ranges
- **Historical Tracking** - View trends and patterns over time

## Architecture

```
┌──────────────────────────────────────────┐
│         Snowscrape Backend               │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Health Endpoint (/health)         │ │
│  │  • Tests DynamoDB, S3, SQS         │ │
│  │  • Reports to Observatory          │ │
│  │  • Returns 200/503 status          │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Metrics Aggregator (hourly)       │ │
│  │  • Queries DynamoDB for job stats  │ │
│  │  • Calculates success rates        │ │
│  │  • Sends batch metrics             │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Observatory Client                │ │
│  │  • Non-blocking HTTP requests      │ │
│  │  • Automatic retry logic           │ │
│  │  • Graceful failure handling       │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
                   │
                   │ HTTPS (with API key auth)
                   ▼
┌──────────────────────────────────────────┐
│      Snowglobe Observatory               │
│  https://snowglobe.alexdiaz.me           │
│                                          │
│  • Health history & uptime tracking     │
│  • Metrics visualization                │
│  • Alert configuration                  │
│  • Event timeline                       │
└──────────────────────────────────────────┘
```

## Setup

### 1. Environment Variables

Add these environment variables to your deployment:

```bash
# Required
export SNOWGLOBE_API_KEY='your-api-key-here'

# Optional (defaults shown)
export SNOWGLOBE_URL='https://snowglobe.alexdiaz.me'
export SNOWGLOBE_SITE_ID='snowscrape'
```

**Security Note:** Never commit `SNOWGLOBE_API_KEY` to version control. Use AWS Secrets Manager, environment variables, or your CI/CD secrets management.

### 2. Register Snowscrape

After deployment, register snowscrape with Observatory:

```bash
cd backend
python register_with_observatory.py --stage dev
```

This creates the service entry in Observatory and enables monitoring.

### 3. Verify Integration

Check that health reporting is working:

```bash
# Trigger health endpoint
curl https://your-api-gateway-url/health

# Check Observatory dashboard
open https://snowglobe.alexdiaz.me/observatory
```

You should see:
- ✅ Snowscrape listed in Observatory
- 🟢 Green status indicator (healthy)
- 📊 Recent health check history
- 📈 Metrics appearing hourly

## What Gets Monitored

### Health Checks (Every Request to `/health`)

- **Status**: healthy | degraded | down
- **Response Time**: Health check duration in ms
- **Service Checks**: DynamoDB, S3, SQS connectivity
- **Error Messages**: Details when services are unhealthy

### Business Metrics (Hourly Aggregation)

| Metric | Description | Source |
|--------|-------------|--------|
| `jobsProcessed` | Total jobs processed in last hour | DynamoDB scan |
| `jobsCompleted` | Successfully completed jobs | DynamoDB filter |
| `jobsFailed` | Failed or timed out jobs | DynamoDB filter |
| `successRate` | Percentage of successful jobs | Calculated |
| `errorRate` | Percentage of failed jobs | Calculated |
| `activeJobs` | Currently processing jobs | DynamoDB count |
| `queueDepth` | Jobs waiting in SQS queue | SQS attributes |
| `urlsCrawled` | URLs processed in last hour | DynamoDB scan |

### Events Tracked

- `metrics_reported` - Hourly metrics sent to Observatory
- `deployment` - New version deployed (manual)
- `critical_error` - DLQ threshold exceeded (manual)

## Viewing Metrics

### In Observatory Dashboard

1. Navigate to https://snowglobe.alexdiaz.me/observatory
2. Find "Snowscrape" in the list
3. Click to view:
   - **Status Badge**: Current health status
   - **Uptime %**: Percentage of successful health checks
   - **Response Time**: Average health check duration
   - **Health History**: Timeline of status changes
   - **Metrics Chart**: Business KPIs over time

### In CloudWatch

CloudWatch is still used for:
- AWS-specific metrics (Lambda throttles, cold starts)
- Detailed execution logs
- X-Ray distributed tracing
- Real-time AWS service metrics

**Division of Responsibility:**
- **Observatory**: Business KPIs, uptime, cross-app comparison
- **CloudWatch**: AWS technical metrics, debugging, operational alarms

## Alerting

Configure alerts in Observatory:

1. Click "Edit" on Snowscrape entry
2. Enable "Alert on Failures"
3. Set thresholds:
   - **Response Time**: Alert if > 5000ms
   - **Consecutive Failures**: Alert after 3 failures
4. Add notification email

Alerts are sent when:
- Health status changes to degraded/down
- Response time exceeds threshold
- Consecutive failures exceed limit

## Code Integration

### Reporting Health

```python
from observatory_client import get_observatory_client

observatory = get_observatory_client()

# Report healthy status
observatory.report_health('healthy', response_time_ms=42)

# Report degraded status
observatory.report_health('degraded',
                         response_time_ms=150,
                         error='DynamoDB slow')

# Report down status
observatory.report_health('down',
                         error='S3 unreachable')
```

### Sending Custom Metrics

```python
observatory.send_metrics({
    'jobsProcessed': 150,
    'successRate': 98.5,
    'avgCrawlDuration': 2500,
    'customMetric': 'value'
})
```

### Tracking Events

```python
observatory.track_event('deployment', {
    'version': '1.2.0',
    'environment': 'production',
    'deployed_by': 'GitHub Actions'
})
```

## Lambda Functions

### Health Check Handler

**Endpoint**: `GET /health`
**Frequency**: On-demand (called by Observatory or monitoring tools)
**Purpose**: Tests service dependencies and reports status

```python
def health_check_handler(event, context):
    # Tests: DynamoDB, S3, SQS
    # Reports to Observatory
    # Returns: 200 (healthy) or 503 (degraded/down)
```

### Metrics Reporter

**Schedule**: Every hour (rate(1 hour))
**Purpose**: Aggregates business metrics and sends to Observatory

```python
def report_metrics_to_observatory_handler(event, context):
    # Queries DynamoDB for job stats
    # Calculates success rates
    # Sends batch metrics
```

## Troubleshooting

### Health not reporting

**Check:**
1. `SNOWGLOBE_API_KEY` is set
2. Network connectivity from Lambda to Observatory
3. CloudWatch logs for errors:
   ```bash
   aws logs tail /aws/lambda/snowscrape-dev-healthCheck --follow
   ```

**Fix:**
- Verify API key is correct
- Check Observatory API is accessible
- Review security group/VPC settings if Lambda is in VPC

### Metrics not appearing

**Check:**
1. Hourly cron is running:
   ```bash
   aws events list-rules --name-prefix snowscrape
   ```
2. CloudWatch logs for `report_metrics_to_observatory_handler`
3. DynamoDB has recent job data

**Fix:**
- Ensure Lambda has DynamoDB read permissions
- Verify SQS queue URL is correct
- Check time-based queries are using correct timezone

### Observatory shows "down" but service works

**Likely causes:**
- Health endpoint timeout (increase Lambda timeout)
- DynamoDB throttling (check CloudWatch metrics)
- Temporary network issue (check history for pattern)

**Fix:**
- Adjust alert thresholds (increase consecutive failures)
- Optimize health check queries
- Add retry logic to health endpoint

## Best Practices

1. **Don't fail on Observatory errors**
   - All Observatory calls are wrapped in try/except
   - Service continues if Observatory is unreachable
   - Logging captures failures for debugging

2. **Keep health checks fast**
   - Target < 1 second response time
   - Use connection pooling
   - Minimize external calls

3. **Monitor both systems**
   - Observatory for business metrics & uptime
   - CloudWatch for AWS technical details
   - Use both for complete visibility

4. **Set appropriate thresholds**
   - Don't alert on single failures (use consecutive)
   - Adjust response time thresholds to your baseline
   - Review alert frequency to avoid fatigue

## Migration from CloudWatch

If you were previously using only CloudWatch:

1. ✅ Keep CloudWatch alarms for AWS-specific issues
2. ✅ Move business KPI alerts to Observatory
3. ✅ Simplify CloudWatch dashboard (remove business widgets)
4. ✅ Point stakeholders to Observatory for business metrics
5. ✅ Keep CloudWatch for engineering/ops debugging

## Additional Resources

- [Observatory Dashboard](https://snowglobe.alexdiaz.me/observatory)
- [Observatory API Documentation](https://snowglobe.alexdiaz.me/help)
- [CloudWatch Dashboard](https://console.aws.amazon.com/cloudwatch/home?region=us-east-2#dashboards:name=snowscrape-dev-operations)

## Support

For Observatory integration issues:
1. Check CloudWatch logs for error details
2. Verify environment variables are set correctly
3. Test Observatory API directly with curl
4. Contact the Observatory team for API issues
