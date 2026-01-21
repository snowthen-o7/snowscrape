#!/bin/bash
# Deploy JavaScript Renderer to AWS ECR and Lambda

set -e

# Configuration
AWS_REGION="us-east-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="snowscrape-js-renderer"
IMAGE_TAG="latest"

echo "=================================================="
echo "SnowScrape JavaScript Renderer Deployment"
echo "=================================================="
echo ""
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "ECR Repository: $ECR_REPOSITORY"
echo ""

# Create ECR repository if it doesn't exist
echo "Creating ECR repository (if not exists)..."
aws ecr describe-repositories \
  --repository-names "$ECR_REPOSITORY" \
  --region "$AWS_REGION" \
  >/dev/null 2>&1 || \
aws ecr create-repository \
  --repository-name "$ECR_REPOSITORY" \
  --region "$AWS_REGION" \
  --image-scanning-configuration scanOnPush=true \
  --tags Key=Project,Value=SnowScrape Key=Component,Value=JSRenderer

echo "✓ ECR repository ready"
echo ""

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo "✓ Logged in to ECR"
echo ""

# Build Docker image
echo "Building Docker image..."
echo "This may take 5-10 minutes (Playwright + Chromium)..."
docker build \
  --platform linux/amd64 \
  -t "$ECR_REPOSITORY:$IMAGE_TAG" \
  -f Dockerfile \
  .

echo "✓ Docker image built"
echo ""

# Tag image for ECR
ECR_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
docker tag "$ECR_REPOSITORY:$IMAGE_TAG" "$ECR_IMAGE_URI"

echo "✓ Image tagged: $ECR_IMAGE_URI"
echo ""

# Push to ECR
echo "Pushing image to ECR..."
echo "This may take several minutes (image is ~1-2GB)..."
docker push "$ECR_IMAGE_URI"

echo "✓ Image pushed to ECR"
echo ""

# Get image digest
IMAGE_DIGEST=$(aws ecr describe-images \
  --repository-name "$ECR_REPOSITORY" \
  --image-ids imageTag="$IMAGE_TAG" \
  --region "$AWS_REGION" \
  --query 'imageDetails[0].imageDigest' \
  --output text)

echo "=================================================="
echo "Deployment Complete!"
echo "=================================================="
echo ""
echo "ECR Image URI: $ECR_IMAGE_URI"
echo "Image Digest: $IMAGE_DIGEST"
echo ""
echo "Next steps:"
echo "1. Update serverless.yml with the image URI"
echo "2. Run 'serverless deploy' to deploy the Lambda function"
echo ""
echo "To test locally:"
echo "  docker run --rm -p 9000:8080 $ECR_REPOSITORY:$IMAGE_TAG"
echo "  curl -X POST \"http://localhost:9000/2015-03-31/functions/function/invocations\" \\"
echo "    -d '{\"url\":\"https://example.com\",\"render_config\":{\"wait_strategy\":\"networkidle\"}}'"
echo ""
echo "Estimated Lambda cost:"
echo "  ~\$0.20 per 1000 renders (2048MB, 10s avg duration)"
echo ""
