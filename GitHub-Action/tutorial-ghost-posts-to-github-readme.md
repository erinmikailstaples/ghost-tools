# Tutorial: Display Recent Ghost Posts on GitHub Profile README

This tutorial will guide you through creating a GitHub Action that automatically updates your GitHub profile README with your latest Ghost blog posts.

## What You'll Learn

- How to fetch data from Ghost's Content API
- How to update GitHub README files automatically
- How to schedule GitHub Actions to run periodically
- How to work with JavaScript/Node.js in GitHub Actions

## Prerequisites

- A Ghost blog (Ghost.org or self-hosted)
- A GitHub account with a profile README repository
- Basic understanding of GitHub Actions
- Familiarity with JavaScript/Node.js

## Step-by-Step Tutorial

### Step 1: Set Up Your Profile README Repository

If you don't have one already, create a repository with the same name as your GitHub username.

```bash
# Example: if your username is "johndoe", create a repository named "johndoe"
# This special repository will display its README on your profile
```

### Step 2: Get Your Ghost Content API Key

1. Go to your Ghost Admin panel
2. Navigate to Settings → Integrations
3. Scroll down to "Content API" section
4. Copy your Content API Key
5. Note your Ghost site URL

### Step 3: Add GitHub Secrets

In your profile repository:
1. Go to Settings → Secrets and variables → Actions
2. Add these secrets:
   - `GHOST_CONTENT_API_KEY`: Your Ghost Content API key
   - `GHOST_SITE_URL`: Your Ghost site URL (e.g., `https://yourblog.ghost.io`)

### Step 4: Create the Action Script

Create `.github/scripts/update-readme.js`:

```javascript
// EXAMPLE SCRIPT - Customize for your needs
const fs = require('fs');
const https = require('https');
const { URL } = require('url');

// Configuration - REPLACE_ME with your values
const GHOST_API_URL = process.env.GHOST_SITE_URL;
const GHOST_API_KEY = process.env.GHOST_CONTENT_API_KEY;
const README_PATH = './README.md';
const POSTS_COUNT = 5; // Number of recent posts to show

// Markers in README.md where posts will be inserted
const START_MARKER = '<!-- GHOST_POSTS_START -->';
const END_MARKER = '<!-- GHOST_POSTS_END -->';

async function fetchGhostPosts() {
  console.log('Fetching recent posts from Ghost...');
  
  const url = new URL(`${GHOST_API_URL}/ghost/api/content/posts/`);
  url.searchParams.append('key', GHOST_API_KEY);
  url.searchParams.append('limit', POSTS_COUNT.toString());
  url.searchParams.append('fields', 'title,slug,published_at,excerpt,feature_image');
  url.searchParams.append('order', 'published_at DESC');

  return new Promise((resolve, reject) => {
    https.get(url.toString(), (response) => {
      let data = '';
      
      response.on('data', (chunk) => {
        data += chunk;
      });
      
      response.on('end', () => {
        try {
          const result = JSON.parse(data);
          if (result.posts) {
            console.log(`Successfully fetched ${result.posts.length} posts`);
            resolve(result.posts);
          } else {
            reject(new Error('No posts found in response'));
          }
        } catch (error) {
          reject(new Error(`Failed to parse response: ${error.message}`));
        }
      });
    }).on('error', (error) => {
      reject(new Error(`HTTP request failed: ${error.message}`));
    });
  });
}

function formatPostsAsMarkdown(posts) {
  console.log('Formatting posts as Markdown...');
  
  let markdown = `## 📝 Latest Blog Posts\\n\\n`;
  
  posts.forEach((post, index) => {
    const postUrl = `${GHOST_API_URL}/${post.slug}/`;
    const publishedDate = new Date(post.published_at).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
    
    markdown += `### ${index + 1}. [${post.title}](${postUrl})\\n`;
    markdown += `*Published on ${publishedDate}*\\n\\n`;
    
    if (post.excerpt) {
      markdown += `${post.excerpt}\\n\\n`;
    }
    
    markdown += `[Read more →](${postUrl})\\n\\n`;
    markdown += '---\\n\\n';
  });
  
  // Remove the last separator
  markdown = markdown.replace(/---\\n\\n$/, '');
  
  return markdown;
}

function updateReadme(newContent) {
  console.log('Updating README.md...');
  
  try {
    const readme = fs.readFileSync(README_PATH, 'utf8');
    
    const startIndex = readme.indexOf(START_MARKER);
    const endIndex = readme.indexOf(END_MARKER);
    
    if (startIndex === -1 || endIndex === -1) {
      throw new Error(`Markers not found in README.md. Please add:\\n${START_MARKER}\\n${END_MARKER}`);
    }
    
    const beforeMarker = readme.substring(0, startIndex + START_MARKER.length);
    const afterMarker = readme.substring(endIndex);
    
    const updatedReadme = `${beforeMarker}\\n${newContent}\\n${afterMarker}`;
    
    fs.writeFileSync(README_PATH, updatedReadme);
    console.log('README.md updated successfully!');
    
    return true;
  } catch (error) {
    console.error(`Failed to update README.md: ${error.message}`);
    return false;
  }
}

async function main() {
  try {
    console.log('Starting Ghost posts update...');
    
    // Validate environment variables
    if (!GHOST_API_URL || !GHOST_API_KEY) {
      throw new Error('Missing required environment variables: GHOST_SITE_URL and GHOST_CONTENT_API_KEY');
    }
    
    // Fetch posts from Ghost
    const posts = await fetchGhostPosts();
    
    if (posts.length === 0) {
      console.log('No posts found. README.md will not be updated.');
      return;
    }
    
    // Format posts as Markdown
    const markdownContent = formatPostsAsMarkdown(posts);
    
    // Update README.md
    const success = updateReadme(markdownContent);
    
    if (success) {
      console.log('✅ Successfully updated GitHub README with latest Ghost posts!');
      
      // Output for GitHub Actions
      console.log(`Updated with ${posts.length} posts`);
    } else {
      process.exit(1);
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

// Run the script
main();
```

### Step 5: Create the GitHub Action Workflow

Create `.github/workflows/update-ghost-posts.yml`:

```yaml
# EXAMPLE: Update GitHub Profile with Ghost Posts
# This is a learning example - customize values marked with REPLACE_ME before using

name: Update README with Ghost Posts

# Schedule the action to run automatically
on:
  schedule:
    # Run every 6 hours (adjust as needed)
    # LEARNING NOTE: Cron syntax - minute hour day month day_of_week
    - cron: '0 */6 * * *'
  
  # Allow manual triggering for testing
  workflow_dispatch:
  
  # Run when README.md is pushed (for initial setup)
  push:
    paths:
      - 'README.md'
      - '.github/workflows/update-ghost-posts.yml'
      - '.github/scripts/update-readme.js'

jobs:
  update-readme:
    runs-on: ubuntu-latest
    
    steps:
    # Step 1: Get the repository code
    - name: Checkout repository
      uses: actions/checkout@v4
      with:
        # This allows the action to commit changes back to the repository
        token: ${{ secrets.GITHUB_TOKEN }}
    
    # Step 2: Set up Node.js environment
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
    
    # Step 3: Run the update script
    - name: Update README with Ghost posts
      env:
        # Pass the secrets as environment variables
        GHOST_SITE_URL: ${{ secrets.GHOST_SITE_URL }}
        GHOST_CONTENT_API_KEY: ${{ secrets.GHOST_CONTENT_API_KEY }}
      run: |
        # Run our custom script
        node .github/scripts/update-readme.js
    
    # Step 4: Commit and push changes (if any)
    - name: Commit changes
      run: |
        # Configure git with a bot user
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        
        # Check if there are any changes to commit
        if git diff --quiet; then
          echo "No changes to commit"
        else
          echo "Changes detected, committing..."
          git add README.md
          git commit -m "📝 Update README with latest Ghost posts"
          git push
        fi
```

### Step 6: Prepare Your README.md

Add these markers to your `README.md` where you want the posts to appear:

```markdown
# Your Name

Welcome to my GitHub profile! I'm a developer who also writes about technology.

## About Me
- 🔭 I'm currently working on...
- 🌱 I'm currently learning...

<!-- GHOST_POSTS_START -->
<!-- This section will be automatically updated with your latest Ghost posts -->
<!-- GHOST_POSTS_END -->

## Other Projects
...rest of your README...
```

### Step 7: Test Your Setup

1. Push all the files to your repository
2. Go to Actions tab in your repository
3. Click on "Update README with Ghost Posts"
4. Click "Run workflow" to test manually
5. Check if your README.md gets updated with your latest posts

## Troubleshooting

### Common Issues

1. **API Key Issues**
   - Verify your Ghost Content API key is correct
   - Ensure your Ghost site URL is correct (no trailing slash)

2. **Markers Not Found**
   - Make sure you have both `<!-- GHOST_POSTS_START -->` and `<!-- GHOST_POSTS_END -->` in your README.md

3. **Permission Errors**
   - The action uses `GITHUB_TOKEN` which should have write permissions by default
   - If issues persist, check your repository's Actions permissions

4. **Rate Limiting**
   - Ghost has API rate limits; don't run the action too frequently
   - The example runs every 6 hours, which should be safe

### Testing Locally

You can test the script locally before deploying:

```bash
# Set environment variables
export GHOST_SITE_URL="https://yourblog.ghost.io"
export GHOST_CONTENT_API_KEY="your-api-key-here"

# Run the script
node .github/scripts/update-readme.js
```

## Customization Ideas

### 1. Add Post Images

Modify the `formatPostsAsMarkdown` function to include feature images:

```javascript
if (post.feature_image) {
  markdown += `![${post.title}](${post.feature_image})\\n\\n`;
}
```

### 2. Filter by Tags

Add tag filtering to the API request:

```javascript
url.searchParams.append('filter', 'tag:tutorial'); // Only posts with 'tutorial' tag
```

### 3. Change the Format

Customize the Markdown format:

```javascript
// Simple list format
markdown += `- [${post.title}](${postUrl}) - ${publishedDate}\\n`;
```

### 4. Add Reading Time

If your Ghost setup includes reading time:

```javascript
url.searchParams.append('fields', 'title,slug,published_at,excerpt,reading_time');

// Then in formatting:
if (post.reading_time) {
  markdown += `*${post.reading_time} min read*\\n\\n`;
}
```

## Security Considerations

- Never commit API keys to your repository
- Use GitHub Secrets for all sensitive information
- Consider using a read-only Content API key
- Review the permissions needed by the GitHub Action

## Next Steps

Once you have this working, you might want to explore:
- Adding RSS feed generation
- Creating a weekly digest email
- Integrating with social media platforms
- Building a full portfolio site generator

This action will keep your GitHub profile fresh and showcase your latest writing automatically!