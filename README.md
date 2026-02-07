# SnowScrape

**SnowScrape** is a serverless web scraping and data extraction platform that allows you to schedule and automate crawling jobs from CSV/TSV files, extract data using XPath, Regex, or JSONPath queries, and store results in S3.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Development Status](#development-status)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

SnowScrape enables users to:
- Define scheduled scraping jobs with customizable intervals
- Parse CSV/TSV files from HTTP/HTTPS or SFTP sources
- Extract URLs from specified columns
- Crawl URLs and extract data using multiple query types
- Store results in AWS S3
- Monitor job execution and status
- Integration with Snowglobe analytics for metrics

---

## Features

### Current Features

#### Core Functionality
- 🕐 **Scheduled Job Execution** - Run scraping jobs automatically at configurable intervals
- 📊 **Multiple Data Sources** - Support for HTTP/HTTPS and SFTP file sources
- 🔍 **Flexible Query Types** - XPath, Regex, and JSONPath query support
- 💾 **S3 Storage** - Automatic result storage in AWS S3
- 🔐 **User Authentication** - Clerk-based authentication system
- 📱 **Web Dashboard** - Modern Next.js UI for job management
- ⚡ **Serverless Architecture** - AWS Lambda-based for automatic scaling
- 📈 **Monitoring Integration** - Snowglobe metrics and monitoring

#### Phase 1 Competitive Features ✨ NEW
- 📦 **Multi-Format Export** - Download results in JSON, CSV, XLSX, Parquet, or SQL formats
- 🔔 **Webhook System** - Event-driven notifications for job lifecycle events (created, started, completed, failed, cancelled)
- 🌐 **AWS Proxy Pool** - Self-hosted proxy infrastructure with geo-targeting (US, EU, Asia) and automatic health checking
- 🎭 **JavaScript Rendering** - Playwright-powered headless browser for scraping SPAs (React, Vue, Angular)

### Planned Features (Phase 2+)

- CAPTCHA solving integration
- Advanced anti-bot detection
- Email notifications
- Job templates UI
- Comprehensive test coverage
- Enhanced error handling and logging
- Performance optimizations

---

## Tech Stack

### Backend

- **Runtime:** Python 3.12
- **Platform:** AWS Lambda (Serverless Framework)
- **Cloud Services:**
  - AWS API Gateway (REST API)
  - AWS DynamoDB (Job metadata, URL tracking, webhooks, proxy pool)
  - AWS S3 (Result storage)
  - AWS SQS (Asynchronous job processing, webhook delivery)
  - AWS CloudWatch (Logging and scheduled events)
  - AWS ECR (Container registry for JS renderer)
  - AWS Lambda Container Images (JavaScript rendering)
  - AWS Secrets Manager (Proxy credentials)
  - AWS EC2 (Proxy infrastructure)
- **Key Libraries:**
  - `boto3` - AWS SDK
  - `beautifulsoup4`, `lxml` - HTML parsing
  - `requests` - HTTP client
  - `paramiko` - SFTP support
  - `pandas` - CSV processing
  - `PyJWT` - Authentication
  - `jsonpath-ng` - JSON querying
  - `openpyxl` - Excel export
  - `pyarrow` - Parquet export
  - `playwright` - JavaScript rendering

### Frontend

- **Framework:** Next.js 16 (React 19)
- **Language:** TypeScript
- **Styling:** Tailwind CSS 3 + Radix UI
- **Authentication:** Clerk
- **Deployment:** Vercel
- **Package Manager:** pnpm
- **Key Libraries:**
  - `@clerk/nextjs` - Authentication
  - `papaparse` - CSV parsing
  - `lucide-react` - Icons
  - `react-toastify` - Notifications

---

## Project Structure

```
snowscrape/
├── backend/                      # Serverless Python backend
│   ├── handler.py               # Lambda function handlers
│   ├── job_manager.py           # Job CRUD operations
│   ├── crawl_manager.py         # Crawl orchestration
│   ├── crawler.py               # Web scraping logic
│   ├── utils.py                 # Utility functions
│   ├── snowglobe.py             # Metrics integration
│   ├── format_converter.py      # Export format conversions (CSV, XLSX, Parquet, SQL)
│   ├── webhook_dispatcher.py    # Webhook event dispatcher
│   ├── webhook_delivery_handler.py  # Webhook delivery Lambda
│   ├── proxy_manager.py         # AWS proxy pool management
│   ├── js_renderer.py           # Playwright JavaScript rendering
│   ├── Dockerfile               # Container image for JS renderer
│   ├── deploy-js-renderer.sh    # Deployment script for ECR
│   ├── serverless.yml           # Serverless Framework config
│   ├── requirements.txt         # Python dependencies
│   └── package.json             # Node.js dependencies (serverless plugins)
│
├── infrastructure/              # CloudFormation templates
│   └── proxy-stack.yml         # EC2 proxy infrastructure
│
├── frontend/
│   └── snowscrape/             # Next.js frontend application
│       ├── app/                # Next.js App Router
│       │   └── (application)/
│       │       ├── dashboard/  # Job dashboard
│       │       └── webhooks/   # Webhook management UI
│       ├── components/         # React components
│       │   ├── JobModal.tsx    # Job creation/editing
│       │   └── JobCard.tsx     # Job list view
│       ├── lib/                # Utilities and helpers
│       │   └── types.ts        # TypeScript interfaces
│       ├── public/             # Static assets
│       └── package.json        # Frontend dependencies
│
├── IMPLEMENTATION_PLAN.md      # Development roadmap (11 phases)
├── ARCHITECTURE.md             # System architecture documentation
└── README.md                   # This file
```

---

## Quick Start

### Prerequisites

- **Node.js** >= 20.x
- **Python** >= 3.12
- **pnpm** (for frontend)
- **AWS Account** with configured credentials
- **Clerk Account** for authentication

### 1. Clone the Repository

```bash
git clone <repository-url>
cd snowscrape
```

### 2. Backend Setup

```bash
cd backend

# Install Node.js dependencies (serverless plugins)
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

# Configure AWS credentials
aws configure

# Deploy to AWS (development)
npx serverless deploy --stage dev
```

See [backend/README.md](./backend/README.md) for detailed backend setup instructions.

### 3. Frontend Setup

```bash
cd frontend/snowscrape

# Install dependencies
pnpm install

# Copy environment variables template
cp .env.example .env.local

# Edit .env.local and add your Clerk API keys and backend API URL

# Run development server
pnpm dev
```

Visit `http://localhost:3000` to access the dashboard.

See [frontend/README.md](./frontend/snowscrape/README.md) for detailed frontend setup instructions.

### 4. Deploy Phase 1 Features (Optional)

#### JavaScript Renderer Container

```bash
cd backend

# Set AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Build and deploy JS renderer to ECR
chmod +x deploy-js-renderer.sh
./deploy-js-renderer.sh

# Deploy updated serverless infrastructure
serverless deploy
```

#### AWS Proxy Pool (Optional)

```bash
# Deploy proxy infrastructure to multiple regions
for region in us-east-1 us-west-2 eu-west-1 ap-southeast-1; do
  aws cloudformation create-stack \
    --stack-name snowscrape-proxy-$region \
    --template-body file://infrastructure/proxy-stack.yml \
    --parameters \
      ParameterKey=ProxyUsername,ParameterValue=snowscrape \
      ParameterKey=ProxyPassword,ParameterValue=$(openssl rand -base64 32) \
    --region $region \
    --capabilities CAPABILITY_IAM
done

# After deployment, store proxy URLs in Secrets Manager
# See deploy script for details
```

---

## Documentation

- **[FEATURES.md](./FEATURES.md)** - Detailed guide to Phase 1 features (Export, Webhooks, Proxies, JS Rendering)
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide for all features
- **[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)** - 11-phase development roadmap
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System architecture and data flow
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history and release notes
- **[backend/README.md](./backend/README.md)** - Backend API documentation
- **[frontend/README.md](./frontend/snowscrape/README.md)** - Frontend development guide

---

## Development Status

SnowScrape is currently in **active development**.

### ✅ Completed - Phase 1: Core Competitive Features

**Feature 1: Multi-Format Export** ✅
- JSON, CSV, XLSX, Parquet, SQL export formats
- Server-side conversion with streaming for large datasets
- S3 caching to avoid redundant conversions
- Frontend dropdown for format selection

**Feature 2: Webhook System** ✅
- Event-driven notifications (job.created, job.started, job.completed, job.failed, job.cancelled)
- SQS-based async delivery with retry logic (max 3 attempts)
- HMAC SHA256 signatures for security
- DynamoDB tables for webhooks and delivery tracking
- Dead Letter Queue for failed deliveries
- Webhook management UI

**Feature 3: AWS Proxy Pool** ✅
- Self-hosted EC2 proxy infrastructure with Squid
- Multi-region deployment (US, EU, Asia) for geo-targeting
- Automatic health checking every 5 minutes
- Proxy rotation strategies (random, round-robin)
- CloudWatch monitoring and metrics
- Secrets Manager for credential storage
- Full proxy configuration UI

**Feature 4: JavaScript Rendering** ✅
- Playwright headless browser for SPAs
- Lambda container images with Chromium
- Multiple wait strategies (load, domcontentloaded, networkidle)
- Optional screenshot capture
- Proxy integration for rendered pages
- Resource blocking capability
- Automatic fallback to standard requests
- Comprehensive rendering configuration UI

### 🚧 In Progress - Phase 2
- CAPTCHA solving integration
- Advanced anti-bot detection
- Email notifications

### Upcoming (See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md))
- Phase 3: Testing infrastructure (80%+ coverage)
- Phase 4: Error handling and logging
- Phase 5: Input validation
- Phase 6: Performance optimizations
- Phase 7: Monitoring and observability
- Phase 8: UX improvements
- Phase 9: Data management and backups
- Phase 10: Security hardening

---

## Environment Variables

### Backend

Configure in AWS Lambda environment variables or `serverless.yml`:

- `DYNAMODB_TABLE` - DynamoDB table name for jobs
- `DYNAMODB_URL_TABLE` - DynamoDB table for URL tracking
- `S3_BUCKET` - S3 bucket for results
- `SQS_QUEUE_URL` - SQS queue URL

### Frontend

Copy `.env.example` to `.env.local` and configure:

```bash
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx

# Backend API
NEXT_PUBLIC_API_URL=https://your-api-gateway-url.amazonaws.com/dev
```

---

## Contributing

This is currently a private project. For development workflow, please refer to:
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for the development roadmap
- Follow the phase-by-phase approach outlined in the plan
- Check off completed items in the implementation plan as you work

---

## License

© 2024-2026 SnowScrape. All rights reserved.

---

## Support

For issues, questions, or feature requests, please refer to the [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) to see if your concern is already being addressed in an upcoming phase.

---

**Last Updated:** January 15, 2026
