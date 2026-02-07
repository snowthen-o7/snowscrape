#!/bin/bash
# Deploy SnowScrape proxy pool to multiple AWS regions

set -e

# Configuration
PROXY_USERNAME="snowscrape"
PROXY_PASSWORD=$(openssl rand -base64 24)
INSTANCE_TYPE="t3.micro"
KEY_NAME=""  # Optional: Set to your EC2 key pair name for SSH access

# Regions to deploy proxies
REGIONS=(
  "us-east-1"
  "us-west-2"
  "eu-west-1"
  "ap-southeast-1"
)

echo "=================================================="
echo "SnowScrape Proxy Pool Deployment"
echo "=================================================="
echo ""
echo "Proxy Username: $PROXY_USERNAME"
echo "Proxy Password: $PROXY_PASSWORD"
echo ""
echo "IMPORTANT: Save these credentials securely!"
echo "They will be used for all proxy instances."
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Store credentials in AWS Secrets Manager
echo ""
echo "Storing credentials in Secrets Manager..."

SECRET_VALUE=$(cat <<EOF
{
  "username": "$PROXY_USERNAME",
  "password": "$PROXY_PASSWORD",
  "proxies": []
}
EOF
)

aws secretsmanager create-secret \
  --name snowscrape/proxy-pool \
  --description "SnowScrape proxy pool credentials and configuration" \
  --secret-string "$SECRET_VALUE" \
  --region us-east-2 \
  2>/dev/null || echo "Secret already exists, skipping creation..."

echo "Credentials stored in Secrets Manager: snowscrape/proxy-pool"

# Deploy to each region
for REGION in "${REGIONS[@]}"; do
  STACK_NAME="snowscrape-proxy-$REGION"

  echo ""
  echo "=================================================="
  echo "Deploying proxy to $REGION"
  echo "Stack: $STACK_NAME"
  echo "=================================================="

  # Check if stack already exists
  if aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    >/dev/null 2>&1; then
    echo "Stack $STACK_NAME already exists in $REGION, skipping..."
    continue
  fi

  # Deploy CloudFormation stack
  aws cloudformation create-stack \
    --stack-name "$STACK_NAME" \
    --template-body file://proxy-stack.yml \
    --parameters \
      ParameterKey=ProxyUsername,ParameterValue="$PROXY_USERNAME" \
      ParameterKey=ProxyPassword,ParameterValue="$PROXY_PASSWORD" \
      ParameterKey=InstanceType,ParameterValue="$INSTANCE_TYPE" \
      $([ -n "$KEY_NAME" ] && echo "ParameterKey=KeyName,ParameterValue=$KEY_NAME") \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --tags \
      Key=Project,Value=SnowScrape \
      Key=Environment,Value=production \
      Key=ManagedBy,Value=deploy-proxies.sh

  echo "Stack creation initiated for $REGION"
done

echo ""
echo "=================================================="
echo "Waiting for all stacks to complete..."
echo "This may take 10-15 minutes..."
echo "=================================================="
echo ""

# Wait for all stacks to complete
PROXIES=()
for REGION in "${REGIONS[@]}"; do
  STACK_NAME="snowscrape-proxy-$REGION"

  echo "Waiting for $STACK_NAME in $REGION..."

  aws cloudformation wait stack-create-complete \
    --stack-name "$STACK_NAME" \
    --region "$REGION" || {
    echo "ERROR: Stack $STACK_NAME failed to create in $REGION"
    echo "Check CloudFormation console for details"
    continue
  }

  # Get proxy IP from stack outputs
  PROXY_IP=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ProxyIP`].OutputValue' \
    --output text)

  INSTANCE_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
    --output text)

  echo "✓ $STACK_NAME deployed successfully"
  echo "  Proxy IP: $PROXY_IP"
  echo "  Instance ID: $INSTANCE_ID"
  echo "  URL: http://$PROXY_USERNAME:***@$PROXY_IP:3128"

  # Add to proxies array for Secrets Manager update
  PROXIES+=("{\"url\":\"http://$PROXY_USERNAME:$PROXY_PASSWORD@$PROXY_IP:3128\",\"region\":\"$REGION\",\"status\":\"healthy\",\"instance_id\":\"$INSTANCE_ID\"}")
done

# Update Secrets Manager with proxy list
echo ""
echo "Updating Secrets Manager with proxy list..."

PROXIES_JSON=$(IFS=,; echo "[${PROXIES[*]}]")

UPDATED_SECRET=$(cat <<EOF
{
  "username": "$PROXY_USERNAME",
  "password": "$PROXY_PASSWORD",
  "proxies": $PROXIES_JSON
}
EOF
)

aws secretsmanager update-secret \
  --secret-id snowscrape/proxy-pool \
  --secret-string "$UPDATED_SECRET" \
  --region us-east-2

echo ""
echo "=================================================="
echo "Deployment Complete!"
echo "=================================================="
echo ""
echo "Deployed ${#PROXIES[@]} proxies across ${#REGIONS[@]} regions"
echo ""
echo "Credentials stored in: snowscrape/proxy-pool (Secrets Manager)"
echo ""
echo "To test a proxy:"
echo "  curl -x http://$PROXY_USERNAME:$PROXY_PASSWORD@<PROXY_IP>:3128 https://ipinfo.io/json"
echo ""
echo "To SSH into a proxy (if KeyName was provided):"
echo "  ssh -i ~/.ssh/your-key.pem ec2-user@<PROXY_IP>"
echo ""
echo "To view proxy logs:"
echo "  aws logs tail /aws/ec2/snowscrape-proxy --follow --region <REGION>"
echo ""
echo "Monthly cost estimate: ~\$${#PROXIES[@]}0 (${#PROXIES[@]} proxies × \$11/month each)"
echo ""
