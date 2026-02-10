#!/usr/bin/env node
const { execSync } = require('child_process');

if (process.env.GITHUB_TOKEN) {
  try {
    console.log('Configuring git authentication for private repositories...');
    execSync(
      `git config --global url."https://${process.env.GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"`,
      { stdio: 'inherit' }
    );
    console.log('Git authentication configured successfully.');
  } catch (error) {
    console.error('Failed to configure git authentication:', error.message);
    process.exit(1);
  }
} else {
  console.log('GITHUB_TOKEN not found, skipping git authentication setup.');
}
