# Setting Up New GitHub Repository for Interns

This guide will help you create a fresh copy of the Barcelona Scraper project for your new interns.

## Prerequisites

- A GitHub account
- Git installed on your machine
- Current project cleaned up (debug files removed)

## Step 1: Create New GitHub Repository

1. Go to [GitHub](https://github.com) and log in
2. Click the "+" icon in the top right corner
3. Select "New repository"
4. Configure your repository:
   - **Repository name**: Choose a name (e.g., `barcelona-scraper-interns`)
   - **Description**: "Barcelona supermarket price scraper - Intern training project"
   - **Visibility**: Choose Public or Private based on your needs
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
5. Click "Create repository"

## Step 2: Add New Remote and Push

After creating the new repository, GitHub will show you instructions. Use these commands:

```bash
# Add the new repository as a remote (replace URL with your new repo URL)
git remote add intern https://github.com/YOUR_USERNAME/barcelona-scraper-interns.git

# Push all branches to the new remote
git push intern main

# Optional: Push any other branches if needed
git push intern --all

# Optional: Push tags if you have any
git push intern --tags
```

## Step 3: Verify the New Repository

1. Navigate to your new repository on GitHub
2. Verify all files are present
3. Check that the README.md displays correctly
4. Ensure all documentation files are visible

## Step 4: Set Up Repository for Interns

### Add Collaborators
1. Go to repository Settings → Collaborators
2. Click "Add people"
3. Add each intern by their GitHub username or email

### Create Issues for Learning Tasks
Create starter issues for interns to work on:
- "Setup development environment"
- "Run first scraper successfully"
- "Add documentation for a scraper"
- "Fix a specific bug or enhancement"

### Protect Main Branch (Optional but Recommended)
1. Go to Settings → Branches
2. Add branch protection rule for `main`
3. Enable:
   - Require pull request reviews before merging
   - Require status checks to pass
   - Include administrators (optional)

## Step 5: Share with Interns

Send interns the following information:

```
Repository URL: https://github.com/YOUR_USERNAME/barcelona-scraper-interns
Clone command: git clone https://github.com/YOUR_USERNAME/barcelona-scraper-interns.git

Please refer to the README.md for setup instructions.
```

## Alternative Method: GitHub Template Repository

If you plan to reuse this setup multiple times:

1. Go to your new repository Settings
2. Check "Template repository"
3. Interns can then create their own copies using "Use this template"

## Managing Multiple Remotes

You can keep both repositories and push to either:

```bash
# View all remotes
git remote -v

# Push to original repo
git push origin main

# Push to intern repo
git push intern main
```

## Important Notes

- ✅ All debug files have been removed
- ✅ Log files have been cleaned up
- ✅ Cache directories removed
- ✅ Project is ready for new developers
- 📝 Ensure interns have access to necessary API keys (Supabase, etc.)
- 📝 Create a separate `.env.example` file with dummy values
- 📝 Consider creating a "Getting Started" video or walkthrough

## Troubleshooting

**Problem**: Push rejected due to large files
**Solution**: The debug files should already be removed. If you encounter this, use `git lfs` for large files.

**Problem**: Interns can't push to main branch
**Solution**: This is intentional if you've set up branch protection. Teach them to use feature branches and pull requests.

**Problem**: Missing dependencies
**Solution**: Ensure `requirements.txt` and `package.json` are up to date before sharing.

## Next Steps for Interns

1. Clone the repository
2. Read README.md and documentation
3. Set up their development environment
4. Review existing scrapers
5. Start with small tasks/issues
6. Create pull requests for review

---

**Created**: October 10, 2025
**Last Updated**: October 10, 2025

