# SnowScrape Infrastructure Documentation

> **Last Updated**: 2026-01-28
> **Maintainer**: Engineering Team
> **Review Frequency**: Monthly or after major infrastructure changes

---

## Overview

**SnowScrape** - Web scraping platform for data extraction and monitoring

**Tech Stack**:
- **Framework:** TBD
- **Language:** TypeScript/Python
- **Scraping:** Puppeteer / Playwright
- **Database:** TBD
- **Storage:** AWS S3
- **Queue:** BullMQ + Redis

**AWS Account**: `282128795857`
**Primary Region**: `us-east-2` (Ohio)

---

## AWS Infrastructure

⚠️ **Status**: To be documented when AWS resources are provisioned.

**Action Items**:
- [ ] Document S3 buckets if file storage is needed
- [ ] Configure CloudFront for CDN (if applicable)
- [ ] Set up IAM users with least-privilege access

---

## Database

**Provider**: TBD (Neon, Supabase, or Railway recommended)
**Type**: PostgreSQL 15+

**Status**: ⚠️ To be provisioned

---

## Authentication

**Provider**: TBD (Clerk, Auth0, or NextAuth recommended)

**Status**: ⚠️ To be configured

---

## Environment Variables

### Development
```bash
NODE_ENV=development
NEXT_PUBLIC_APP_URL=http://localhost:3000
GITHUB_TOKEN=ghp_your_github_token_here  # For @snowforge/ui private repo access
```

### Production
```bash
NODE_ENV=production
NEXT_PUBLIC_APP_URL=https://snowscrape.yourdomain.com
GITHUB_TOKEN=ghp_your_github_token_here  # For @snowforge/ui private repo access
```

**Critical Environment Variables**:
- `GITHUB_TOKEN` - GitHub Personal Access Token with `repo` scope for accessing private @snowforge/ui repository

---

## Private Repository Authentication

**Required for CI/CD**: Access to private @snowforge/ui shared component library

### Setup Process

1. **Create GitHub Personal Access Token**:
   - Visit: https://github.com/settings/tokens
   - Generate new token (classic)
   - Name: "SnowScrape Deployment"
   - Scope: `repo` (Full control of private repositories)
   - Expiration: 90 days or no expiration (for CI/CD)

2. **Local Development Setup**:
   ```powershell
   # PowerShell - Add to profile for persistence
   notepad $PROFILE
   # Add: $env:GITHUB_TOKEN="ghp_your_token_here"

   # For current session only:
   $env:GITHUB_TOKEN="ghp_your_token_here"
   pnpm install
   ```

3. **Vercel Environment Variables**:
   - Go to: Vercel Dashboard → Project Settings → Environment Variables
   - Add: `GITHUB_TOKEN` = `ghp_your_token_here`
   - Apply to: All environments (Production, Preview, Development)

4. **How it Works**:
   - Script: `scripts/setup-git-auth.js` configures git credentials
   - Vercel runs: `node scripts/setup-git-auth.js && pnpm install --no-frozen-lockfile`
   - Git automatically injects token when cloning @snowforge/ui
   - Build succeeds with proper authentication

**Security Notes**:
- ✅ `.npmrc` is gitignored to prevent token exposure
- ✅ Token uses environment variable interpolation
- ✅ Script only runs in CI/CD environments
- ⚠️ Rotate tokens every 90 days or after exposure

---

## Deployment Architecture

**Hosting**: TBD (Vercel recommended for Next.js/React apps)

**Action Items**:
- [ ] Set up hosting environment
- [ ] Configure custom domain
- [ ] Set up staging environment

---

## Cost Management

**Total Estimated Monthly Cost**: TBD (to be calculated when infrastructure is provisioned)

---

## Security

**Best Practices**:
- ✅ All secrets in environment variables
- ✅ HTTPS only
- ⚠️ TODO: Configure security headers
- ⚠️ TODO: Implement rate limiting

---

## Maintenance Checklist

### Monthly
- [ ] **Review and update this document**
- [ ] Check costs and optimize
- [ ] Update dependencies

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-28 | Added Private Repository Authentication section for @snowforge/ui access | Engineering Team |
| 2026-01-26 | Initial infrastructure documentation created | Engineering Team |

---

*This document should be reviewed and updated monthly or after any major infrastructure changes.*
