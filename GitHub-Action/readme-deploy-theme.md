# Auto-Update Ghost Theme from GitHub using GitHub Actions

This guide explains how to set up a GitHub Action that automatically updates your Ghost theme from GitHub to Ghost.org whenever changes are pushed to your repository.

## Overview

The GitHub Action will:
1. Trigger on push to main branch (or specified branches)
2. Build/prepare your theme files
3. Create a zip package of your theme
4. Upload the theme to your Ghost site via the Admin API

## Prerequisites

- A Ghost site (Ghost.org or self-hosted with Admin API enabled)
- A GitHub repository containing your Ghost theme
- Ghost Admin API credentials

## Setup Instructions

### 1. Get Ghost Admin API Credentials

1. Go to your Ghost Admin panel
2. Navigate to Settings → Integrations
3. Create a new custom integration
4. Note down the Admin API Key and API URL

### 2. Add GitHub Secrets

In your GitHub repository, go to Settings → Secrets and variables → Actions, then add:

- `GHOST_ADMIN_API_KEY`: Your Ghost Admin API key
- `GHOST_API_URL`: Your Ghost site API URL (e.g., `https://yourblog.ghost.io`)

### 3. Create the GitHub Action Workflow

Create `.github/workflows/deploy-theme.yml` in your repository:

```yaml
name: Deploy Ghost Theme

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
      
    - name: Build theme (if needed)
      run: npm run build
      # Remove this step if your theme doesn't need building
      
    - name: Create theme package
      run: |
        # Remove development files
        rm -rf node_modules
        rm -rf .git
        rm -rf .github
        rm -f package-lock.json
        rm -f .gitignore
        
        # Create zip file
        zip -r theme.zip . -x "*.git*" "*node_modules*" "*.DS_Store*"
        
    - name: Deploy to Ghost
      uses: actions/upload-artifact@v4
      with:
        name: theme-package
        path: theme.zip
        
    - name: Upload theme to Ghost
      run: |
        curl -X POST \
          -H "Authorization: Ghost ${{ secrets.GHOST_ADMIN_API_KEY }}" \
          -H "Accept-Version: v5.0" \
          -F "file=@theme.zip" \
          "${{ secrets.GHOST_API_URL }}/admin/themes/upload/"
```

## Alternative: Using Ghost CLI Action

You can also use the community-maintained Ghost CLI action:

```yaml
name: Deploy Ghost Theme

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        
    - name: Install Ghost CLI
      run: npm install -g ghost-cli@latest
      
    - name: Deploy theme
      run: |
        ghost theme upload \
          --url ${{ secrets.GHOST_API_URL }} \
          --key ${{ secrets.GHOST_ADMIN_API_KEY }}
```

## Theme Structure Requirements

Ensure your Ghost theme follows the proper structure:

```
your-theme/
├── assets/
├── partials/
├── default.hbs
├── index.hbs
├── post.hbs
├── package.json
└── ...other theme files
```

## package.json Configuration

Your `package.json` should include Ghost theme configuration:

```json
{
  "name": "your-theme-name",
  "version": "1.0.0",
  "engines": {
    "ghost": ">=5.0.0"
  },
  "config": {
    "posts_per_page": 10
  }
}
```

## Troubleshooting

### Common Issues

1. **Authentication errors**: Verify your API key and URL are correct
2. **Theme validation errors**: Ensure your theme follows Ghost theme requirements
3. **Build failures**: Check that all dependencies are properly listed in package.json

### Testing Locally

Before setting up the action, test theme upload manually:

```bash
# Install Ghost CLI
npm install -g ghost-cli

# Upload theme
ghost theme upload --zip theme.zip --url YOUR_SITE_URL --key YOUR_API_KEY
```

## Security Best Practices

- Never commit API keys to your repository
- Use GitHub Secrets for all sensitive information
- Consider using environment-specific deployments (staging vs production)
- Review the uploaded theme in Ghost admin before activating

## Advanced Configuration

### Environment-specific Deployments

You can set up different workflows for staging and production:

```yaml
on:
  push:
    branches: 
      - main        # Production
      - develop     # Staging
      
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      # ... other steps ...
      
    - name: Set environment
      run: |
        if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
          echo "GHOST_URL=${{ secrets.PROD_GHOST_API_URL }}" >> $GITHUB_ENV
          echo "GHOST_KEY=${{ secrets.PROD_GHOST_ADMIN_API_KEY }}" >> $GITHUB_ENV
        else
          echo "GHOST_URL=${{ secrets.STAGING_GHOST_API_URL }}" >> $GITHUB_ENV  
          echo "GHOST_KEY=${{ secrets.STAGING_GHOST_ADMIN_API_KEY }}" >> $GITHUB_ENV
        fi
```

This setup ensures your Ghost theme automatically updates whenever you push changes to GitHub!