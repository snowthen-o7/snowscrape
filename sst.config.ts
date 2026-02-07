/// <reference path="./.sst/platform/config.d.ts" />

export default $config({
  app(input) {
    return {
      name: "snowscrape",
      removal: input?.stage === "prod" ? "retain" : "remove",
      protect: ["prod"].includes(input?.stage ?? ""),
      home: "aws",
      providers: {
        aws: {
          region: "us-east-2",
        },
      },
    };
  },
  async run() {
    const stage = $app.stage;

    // ─── Stage-Specific Configuration ─────────────────────────────────

    const corsOrigin: Record<string, string> = {
      dev: "http://localhost:3001",
      staging: "https://staging.snowscrape.alexdiaz.me",
      prod: "https://snowscrape.alexdiaz.me",
    };

    const alarmEmail: Record<string, string> = {
      dev: "dev-alerts@example.com",
      staging: "dev-alerts@example.com",
      prod: "ops-alerts@example.com",
    };

    // ─── Clerk Keys from SSM Parameter Store ──────────────────────────

    const clerkJwtPublicKey = new sst.Secret("ClerkJwtPublicKey");
    const clerkJwtSecretKey = new sst.Secret("ClerkJwtSecretKey");

    // ─── DynamoDB Tables ──────────────────────────────────────────────

    const jobsTable = new sst.aws.Dynamo("Jobs", {
      fields: {
        job_id: "string",
        status: "string",
        jobStatus: "string",
        nextRun: "string",
      },
      primaryIndex: { hashKey: "job_id" },
      globalIndexes: {
        StatusIndex: { hashKey: "status" },
        ScheduleIndex: { hashKey: "jobStatus", rangeKey: "nextRun" },
      },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
        },
      },
    });

    const sessionsTable = new sst.aws.Dynamo("Sessions", {
      fields: {
        job_id: "string",
      },
      primaryIndex: { hashKey: "job_id" },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
        },
      },
    });

    const urlsTable = new sst.aws.Dynamo("Urls", {
      fields: {
        job_id: "string",
        url: "string",
        status: "string",
      },
      primaryIndex: { hashKey: "job_id", rangeKey: "url" },
      globalIndexes: {
        StatusIndex: { hashKey: "status" },
      },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
        },
      },
    });

    const templatesTable = new sst.aws.Dynamo("Templates", {
      fields: {
        template_id: "string",
        user_id: "string",
      },
      primaryIndex: { hashKey: "template_id" },
      globalIndexes: {
        UserIdIndex: { hashKey: "user_id" },
      },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
        },
      },
    });

    const webhooksTable = new sst.aws.Dynamo("Webhooks", {
      fields: {
        webhook_id: "string",
        user_id: "string",
      },
      primaryIndex: { hashKey: "webhook_id" },
      globalIndexes: {
        UserIdIndex: { hashKey: "user_id" },
      },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
        },
      },
    });

    const webhookDeliveriesTable = new sst.aws.Dynamo("WebhookDeliveries", {
      fields: {
        delivery_id: "string",
        webhook_id: "string",
        timestamp: "number",
      },
      primaryIndex: { hashKey: "delivery_id" },
      globalIndexes: {
        WebhookIdIndex: {
          hashKey: "webhook_id",
          rangeKey: "timestamp",
        },
      },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
          ttl: { attributeName: "ttl", enabled: true },
        },
      },
    });

    const proxyPoolTable = new sst.aws.Dynamo("ProxyPool", {
      fields: {
        proxy_id: "string",
      },
      primaryIndex: { hashKey: "proxy_id" },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
        },
      },
    });

    const connectionsTable = new sst.aws.Dynamo("Connections", {
      fields: {
        connection_id: "string",
      },
      primaryIndex: { hashKey: "connection_id" },
      transform: {
        table: {
          serverSideEncryption: { enabled: true },
          ttl: { attributeName: "ttl", enabled: true },
        },
      },
    });

    // ─── SQS Queues ───────────────────────────────────────────────────

    const jobDlq = new sst.aws.Queue("JobDLQ", {
      transform: {
        queue: {
          messageRetentionSeconds: 1209600, // 14 days
          visibilityTimeoutSeconds: 300,
        },
      },
    });

    const jobQueue = new sst.aws.Queue("JobQueue", {
      dlq: {
        queue: jobDlq.arn,
        retry: 3,
      },
      transform: {
        queue: {
          visibilityTimeoutSeconds: 900, // 15 minutes (matches Lambda timeout)
          messageRetentionSeconds: 345600, // 4 days
          receiveWaitTimeSeconds: 20, // Long polling
        },
      },
    });

    const webhookDlq = new sst.aws.Queue("WebhookDLQ", {
      transform: {
        queue: {
          messageRetentionSeconds: 1209600, // 14 days
          visibilityTimeoutSeconds: 60,
        },
      },
    });

    const webhookQueue = new sst.aws.Queue("WebhookQueue", {
      dlq: {
        queue: webhookDlq.arn,
        retry: 3,
      },
      transform: {
        queue: {
          visibilityTimeoutSeconds: 60, // Matches Lambda timeout
          messageRetentionSeconds: 345600, // 4 days
          receiveWaitTimeSeconds: 20, // Long polling
        },
      },
    });

    // ─── S3 Bucket ────────────────────────────────────────────────────

    const resultsBucket = new sst.aws.Bucket("Results", {
      versioning: true,
      transform: {
        bucket: {
          serverSideEncryptionConfiguration: {
            rule: {
              applyServerSideEncryptionByDefault: {
                sseAlgorithm: "AES256",
              },
            },
          },
          tags: {
            Project: "Snowscrape",
            Environment: stage,
            ManagedBy: "SST",
          },
        },
      },
    });

    // S3 lifecycle rules
    new aws.s3.BucketLifecycleConfigurationV2("ResultsLifecycle", {
      bucket: resultsBucket.name,
      rules: [
        {
          id: "MoveToGlacierAfter90Days",
          status: "Enabled",
          transitions: [
            {
              days: 90,
              storageClass: "GLACIER",
            },
          ],
        },
        {
          id: "DeleteAfter365Days",
          status: "Enabled",
          expiration: {
            days: 365,
          },
        },
        {
          id: "CleanupIncompleteMultipartUploads",
          status: "Enabled",
          abortIncompleteMultipartUpload: {
            daysAfterInitiation: 7,
          },
        },
      ],
    });

    // ─── Shared Environment Variables ─────────────────────────────────

    const sharedEnv = {
      DYNAMODB_JOBS_TABLE: jobsTable.name,
      DYNAMODB_SESSION_TABLE: sessionsTable.name,
      DYNAMODB_URLS_TABLE: urlsTable.name,
      DYNAMODB_TEMPLATES_TABLE: templatesTable.name,
      DYNAMODB_WEBHOOKS_TABLE: webhooksTable.name,
      DYNAMODB_WEBHOOK_DELIVERIES_TABLE: webhookDeliveriesTable.name,
      DYNAMODB_PROXY_POOL_TABLE: proxyPoolTable.name,
      DYNAMODB_CONNECTIONS_TABLE: connectionsTable.name,
      REGION: "us-east-2",
      S3_BUCKET: resultsBucket.name,
      SQS_JOB_QUEUE: jobQueue.url,
      SQS_JOB_QUEUE_URL: jobQueue.url,
      SQS_WEBHOOK_QUEUE: webhookQueue.url,
      SQS_WEBHOOK_QUEUE_URL: webhookQueue.url,
      CORS_ALLOWED_ORIGIN: corsOrigin[stage] ?? corsOrigin.dev,
      CLERK_JWT_PUBLIC_KEY: clerkJwtPublicKey.value,
      CLERK_JWT_SECRET_KEY: clerkJwtSecretKey.value,
      SNOWGLOBE_URL: "https://snowglobe.alexdiaz.me",
      SNOWGLOBE_SITE_ID: "snowscrape",
    };

    // ─── Shared Lambda Permissions ────────────────────────────────────

    const allTables = [
      jobsTable,
      sessionsTable,
      urlsTable,
      templatesTable,
      webhooksTable,
      webhookDeliveriesTable,
      proxyPoolTable,
      connectionsTable,
    ];

    // ─── Default Python Lambda Config ─────────────────────────────────

    const pythonDefaults = {
      runtime: "python3.11" as const,
      memory: "512 MB" as const,
      timeout: "30 seconds" as const,
      environment: sharedEnv,
      link: [...allTables, jobQueue, webhookQueue, resultsBucket],
    };

    // ─── HTTP API ─────────────────────────────────────────────────────

    const api = new sst.aws.ApiGatewayV2("Api", {
      cors: {
        allowOrigins: [corsOrigin[stage] ?? corsOrigin.dev],
        allowMethods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allowHeaders: [
          "Content-Type",
          "X-Amz-Date",
          "Authorization",
          "X-Api-Key",
          "X-Amz-Security-Token",
          "X-Amz-User-Agent",
        ],
        allowCredentials: true,
        maxAge: "24 hours",
      },
    });

    // Health check
    api.route("GET /health", {
      ...pythonDefaults,
      handler: "backend/handler.health_check_handler",
      memory: "256 MB",
      timeout: "10 seconds",
    });

    // Jobs CRUD
    api.route("POST /jobs", {
      ...pythonDefaults,
      handler: "backend/handler.create_job_handler",
    });

    api.route("GET /jobs/status", {
      ...pythonDefaults,
      handler: "backend/handler.get_all_job_statuses_handler",
    });

    api.route("GET /jobs/{job_id}", {
      ...pythonDefaults,
      handler: "backend/handler.get_job_details_handler",
    });

    api.route("PUT /jobs/{job_id}", {
      ...pythonDefaults,
      handler: "backend/handler.update_job_handler",
    });

    api.route("DELETE /jobs/{job_id}", {
      ...pythonDefaults,
      handler: "backend/handler.delete_job_handler",
    });

    api.route("PATCH /jobs/{job_id}/pause", {
      ...pythonDefaults,
      handler: "backend/handler.pause_job_handler",
    });

    api.route("PATCH /jobs/{job_id}/cancel", {
      ...pythonDefaults,
      handler: "backend/handler.cancel_job_handler",
    });

    api.route("PATCH /jobs/{job_id}/resume", {
      ...pythonDefaults,
      handler: "backend/handler.resume_job_handler",
    });

    api.route("POST /jobs/{job_id}/refresh", {
      ...pythonDefaults,
      handler: "backend/handler.refresh_job_handler",
    });

    // Crawl details
    api.route("GET /jobs/{job_id}/crawls", {
      ...pythonDefaults,
      handler: "backend/handler.get_job_crawls_handler",
    });

    api.route("GET /jobs/{job_id}/crawls/{crawl_id}", {
      ...pythonDefaults,
      handler: "backend/handler.get_crawl_handler",
    });

    // Results
    api.route("GET /jobs/{job_id}/download", {
      ...pythonDefaults,
      handler: "backend/handler.download_results_handler",
    });

    api.route("GET /jobs/{job_id}/preview", {
      ...pythonDefaults,
      handler: "backend/handler.preview_results_handler",
    });

    // Templates
    api.route("POST /templates", {
      ...pythonDefaults,
      handler: "backend/handler.create_template_handler",
      timeout: "10 seconds",
    });

    api.route("GET /templates", {
      ...pythonDefaults,
      handler: "backend/handler.list_templates_handler",
      timeout: "10 seconds",
    });

    api.route("GET /templates/{template_id}", {
      ...pythonDefaults,
      handler: "backend/handler.get_template_handler",
      timeout: "10 seconds",
    });

    api.route("DELETE /templates/{template_id}", {
      ...pythonDefaults,
      handler: "backend/handler.delete_template_handler",
      timeout: "10 seconds",
    });

    // Webhooks
    api.route("POST /webhooks", {
      ...pythonDefaults,
      handler: "backend/handler.create_webhook_handler",
      timeout: "10 seconds",
    });

    api.route("GET /webhooks", {
      ...pythonDefaults,
      handler: "backend/handler.list_webhooks_handler",
      timeout: "10 seconds",
    });

    api.route("DELETE /webhooks/{webhook_id}", {
      ...pythonDefaults,
      handler: "backend/handler.delete_webhook_handler",
      timeout: "10 seconds",
    });

    api.route("POST /webhooks/{webhook_id}/test", {
      ...pythonDefaults,
      handler: "backend/handler.test_webhook_handler",
      timeout: "10 seconds",
    });

    // Validation & Preview
    api.route("POST /validate-sftp-url", {
      ...pythonDefaults,
      handler: "backend/handler.validate_sftp_url_handler",
    });

    api.route("POST /preview-url", {
      ...pythonDefaults,
      handler: "backend/handler.preview_url_variables_handler",
    });

    // Scraper Visual Builder
    api.route("POST /scraper/preview", {
      ...pythonDefaults,
      handler: "backend/handler.scraper_preview_handler",
      timeout: "90 seconds",
    });

    api.route("POST /scraper/test", {
      ...pythonDefaults,
      handler: "backend/handler.scraper_test_handler",
      timeout: "90 seconds",
    });

    // Async worker (no HTTP event — invoked directly by async start)
    const asyncWorker = new sst.aws.Function("ScraperPreviewAsyncWorker", {
      ...pythonDefaults,
      handler: "backend/handler.scraper_preview_async_worker_handler",
      memory: "512 MB",
      timeout: "120 seconds",
    });

    // Async Scraper (needs invoke permission for worker)
    api.route("POST /scraper/preview/async", {
      ...pythonDefaults,
      handler: "backend/handler.scraper_preview_async_start_handler",
      memory: "256 MB",
      timeout: "10 seconds",
      environment: {
        ...sharedEnv,
        ASYNC_WORKER_FUNCTION_NAME: asyncWorker.name,
      },
      permissions: [
        {
          actions: ["lambda:InvokeFunction"],
          resources: [asyncWorker.arn],
        },
      ],
    });

    // ─── WebSocket API ────────────────────────────────────────────────

    const wsApi = new sst.aws.ApiGatewayWebSocket("WsApi");

    wsApi.route("$connect", {
      ...pythonDefaults,
      handler: "backend/websocket_handler.ws_connect_handler",
      memory: "256 MB",
      timeout: "10 seconds",
    });

    wsApi.route("$disconnect", {
      ...pythonDefaults,
      handler: "backend/websocket_handler.ws_disconnect_handler",
      memory: "256 MB",
      timeout: "10 seconds",
    });

    wsApi.route("$default", {
      ...pythonDefaults,
      handler: "backend/websocket_handler.ws_default_handler",
      memory: "256 MB",
      timeout: "10 seconds",
    });

    // ─── SQS Subscribers ──────────────────────────────────────────────

    jobQueue.subscribe(
      {
        ...pythonDefaults,
        handler: "backend/handler.process_job_handler",
        memory: "1024 MB",
        timeout: "900 seconds",
      },
      {
        batch: {
          size: 5,
          partialResponses: true,
        },
      },
    );

    webhookQueue.subscribe(
      {
        ...pythonDefaults,
        handler:
          "backend/webhook_delivery_handler.webhook_delivery_handler",
        memory: "512 MB",
        timeout: "60 seconds",
      },
      {
        batch: {
          size: 10,
          partialResponses: true,
        },
      },
    );

    // ─── Cron Jobs ────────────────────────────────────────────────────

    new sst.aws.Cron("ScheduleJobs", {
      schedule: "rate(5 minutes)",
      job: {
        ...pythonDefaults,
        handler: "backend/handler.schedule_jobs_handler",
        memory: "512 MB",
        timeout: "60 seconds",
      },
    });

    new sst.aws.Cron("ReportMetrics", {
      schedule: "rate(1 hour)",
      job: {
        ...pythonDefaults,
        handler: "backend/handler.report_metrics_to_observatory_handler",
        memory: "512 MB",
        timeout: "60 seconds",
      },
    });

    new sst.aws.Cron("CleanupOldResults", {
      schedule: "rate(1 day)",
      job: {
        ...pythonDefaults,
        handler: "backend/handler.cleanup_old_results_handler",
        memory: "512 MB",
        timeout: "300 seconds",
      },
    });

    new sst.aws.Cron("ProxyHealthChecker", {
      schedule: "rate(5 minutes)",
      job: {
        ...pythonDefaults,
        handler: "backend/handler.proxy_health_checker_handler",
        memory: "256 MB",
        timeout: "60 seconds",
      },
    });

    // ─── Monitoring ───────────────────────────────────────────────────

    const alarmTopic = new aws.sns.Topic("AlarmTopic", {
      displayName: "Snowscrape Alarm Notifications",
    });

    new aws.sns.TopicSubscription("AlarmEmail", {
      topic: alarmTopic.arn,
      protocol: "email",
      endpoint: alarmEmail[stage] ?? alarmEmail.dev,
    });

    // High Error Rate Alarm
    new aws.cloudwatch.MetricAlarm("HighErrorRate", {
      name: `snowscrape-${stage}-high-error-rate`,
      metricName: "JobProcessingErrors",
      namespace: `snowscrape/${stage}`,
      statistic: "Sum",
      period: 300,
      evaluationPeriods: 1,
      threshold: 10,
      comparisonOperator: "GreaterThanThreshold",
      treatMissingData: "notBreaching",
      alarmActions: [alarmTopic.arn],
      okActions: [alarmTopic.arn],
    });

    // DLQ Messages Alarm
    new aws.cloudwatch.MetricAlarm("DLQMessages", {
      name: `snowscrape-${stage}-dlq-messages`,
      metricName: "ApproximateNumberOfMessagesVisible",
      namespace: "AWS/SQS",
      dimensions: { QueueName: jobDlq.nodes.queue.name },
      statistic: "Sum",
      period: 300,
      evaluationPeriods: 1,
      threshold: 1,
      comparisonOperator: "GreaterThanOrEqualToThreshold",
      treatMissingData: "notBreaching",
      alarmActions: [alarmTopic.arn],
      okActions: [alarmTopic.arn],
    });

    // Lambda Errors Alarm
    new aws.cloudwatch.MetricAlarm("LambdaErrors", {
      name: `snowscrape-${stage}-lambda-errors`,
      metricName: "Errors",
      namespace: "AWS/Lambda",
      statistic: "Sum",
      period: 300,
      evaluationPeriods: 2,
      threshold: 5,
      comparisonOperator: "GreaterThanThreshold",
      treatMissingData: "notBreaching",
      alarmActions: [alarmTopic.arn],
    });

    // Lambda Throttles Alarm
    new aws.cloudwatch.MetricAlarm("LambdaThrottles", {
      name: `snowscrape-${stage}-lambda-throttles`,
      metricName: "Throttles",
      namespace: "AWS/Lambda",
      statistic: "Sum",
      period: 300,
      evaluationPeriods: 1,
      threshold: 1,
      comparisonOperator: "GreaterThanThreshold",
      treatMissingData: "notBreaching",
      alarmActions: [alarmTopic.arn],
    });

    // API Gateway 5xx Errors Alarm
    new aws.cloudwatch.MetricAlarm("Api5xxErrors", {
      name: `snowscrape-${stage}-api-5xx-errors`,
      metricName: "5xx",
      namespace: "AWS/ApiGateway",
      statistic: "Sum",
      period: 300,
      evaluationPeriods: 1,
      threshold: 10,
      comparisonOperator: "GreaterThanThreshold",
      treatMissingData: "notBreaching",
      alarmActions: [alarmTopic.arn],
    });

    // ─── Outputs ──────────────────────────────────────────────────────

    return {
      apiUrl: api.url,
      wsUrl: wsApi.url,
      resultsBucket: resultsBucket.name,
    };
  },
});
