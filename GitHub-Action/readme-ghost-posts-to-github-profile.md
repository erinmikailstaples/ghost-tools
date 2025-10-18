# Ghost Posts to GitHub Profile README

Automatically display your latest Ghost blog posts on your GitHub profile README using GitHub Actions.

## Quick Overview

This GitHub Action fetches your recent Ghost blog posts via the Content API and updates your GitHub profile README with them. The action runs on a schedule (every 6 hours by default) and whenever you push changes to the workflow files.

## What It Does

- 📝 Fetches your latest Ghost blog posts
- 🔄 Updates your GitHub profile README automatically  
- ⏰ Runs on a schedule (customizable)
- 🎨 Formats posts with titles, dates, excerpts, and links
- 🔒 Uses secure GitHub Secrets for API keys

## Quick Setup

### 1. Repository Setup
Create a repository with the same name as your GitHub username (this enables the profile README feature).

### 2. Get Ghost API Credentials
- Go to your Ghost Admin → Settings → Integrations
- Copy your Content API Key and site URL

### 3. Add GitHub Secrets
In your profile repository, go to Settings → Secrets and variables → Actions:
- `GHOST_CONTENT_API_KEY`: Your Ghost Content API key
- `GHOST_SITE_URL`: Your Ghost site URL (e.g., `https://yourblog.ghost.io`)

### 4. Add Files to Your Repository

Copy these files to your repository:

**`.github/workflows/update-ghost-posts.yml`** (the GitHub Action)
**`.github/scripts/update-readme.js`** (the update script)

### 5. Prepare Your README
Add these markers to your `README.md` where you want posts to appear:

```markdown
<!-- GHOST_POSTS_START -->
<!-- This section will be automatically updated -->
<!-- GHOST_POSTS_END -->
```

### 6. Test
Go to Actions tab → "Update README with Ghost Posts" → "Run workflow"

## Configuration Options

### Change Update Frequency
Edit the cron schedule in the workflow file:
```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
  - cron: '0 9 * * *'    # Daily at 9 AM
  - cron: '0 9 * * 1'    # Weekly on Monday at 9 AM
```

### Customize Number of Posts
In the JavaScript file, change:
```javascript
const POSTS_COUNT = 5; // Show 5 recent posts
```

### Filter Posts by Tag
Add tag filtering to only show specific posts:
```javascript
url.searchParams.append('filter', 'tag:tutorial');
```

### Change Post Format
Customize the Markdown formatting in the `formatPostsAsMarkdown` function.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Posts not appearing** | Check that markers are in README.md and secrets are set correctly |
| **API errors** | Verify Ghost site URL (no trailing slash) and API key |
| **Permission errors** | Ensure Actions have write permissions in repository settings |
| **Action not running** | Check the cron schedule and that workflow file is in `.github/workflows/` |

## File Structure

```
your-username/              # Your profile repository
├── README.md              # Your profile README
├── .github/
│   ├── workflows/
│   │   └── update-ghost-posts.yml    # GitHub Action workflow  
│   └── scripts/
│       └── update-readme.js          # Update script
```

## Example Output

Your README will be updated with something like this:

```markdown
## 📝 Latest Blog Posts

### 1. [Getting Started with GitHub Actions](https://yourblog.ghost.io/github-actions-guide/)
*Published on October 15, 2024*

Learn how to automate your development workflow with GitHub Actions. This comprehensive guide covers everything from basic concepts to advanced techniques.

[Read more →](https://yourblog.ghost.io/github-actions-guide/)

---

### 2. [Building Modern Web Apps](https://yourblog.ghost.io/modern-web-apps/)
*Published on October 10, 2024*

Explore the latest trends and technologies in modern web development.

[Read more →](https://yourblog.ghost.ghost.io/modern-web-apps/)
```

## Customization Ideas

### Add Featured Images
```javascript
if (post.feature_image) {
  markdown += `![${post.title}](${post.feature_image})\n\n`;
}
```

### Include Reading Time
```javascript
if (post.reading_time) {
  markdown += `*${post.reading_time} min read*\n\n`;
}
```

### Simple List Format
```javascript
markdown += `- [${post.title}](${postUrl}) - ${publishedDate}\n`;
```

## Security Notes

- ✅ Uses read-only Ghost Content API (not Admin API)
- ✅ API keys stored securely as GitHub Secrets
- ✅ No sensitive data exposed in logs or code
- ✅ Automatic cleanup of temporary data

## Other Ghost Tools You Might Like

### 1. **Theme Auto-Deploy**
Deploy your Ghost theme automatically from GitHub → Ghost.org

### 2. **Content Backup**
Backup your Ghost content to GitHub regularly  

### 3. **Newsletter Archive**
Create a GitHub Pages site with your newsletter archive

### 4. **Social Media Auto-Post**
Share new Ghost posts automatically on social media

### 5. **SEO Monitor**
Track SEO metrics and generate reports

### 6. **Comment System Integration**
Sync comments between Ghost and external services

### 7. **Analytics Dashboard**
Generate custom analytics reports from Ghost data

### 8. **Multi-site Management**
Manage multiple Ghost sites from one dashboard

## Support

- 📖 [Full Tutorial](tutorial-ghost-posts-to-github-readme.md)
- 🐛 Found an issue? Check the troubleshooting section
- 💡 Want to contribute? Open a pull request
- ❓ Questions? Open an issue

## License

Feel free to use, modify, and distribute this code for your own projects.

---

*This tool helps you showcase your writing and keep your GitHub profile active automatically!* 🚀