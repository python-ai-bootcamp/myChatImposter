---
description: Run ESLint on frontend code after making changes
---

# Frontend Lint Check

Run this after making any changes to frontend JavaScript/JSX files to catch errors and warnings before rebuilding containers.

// turbo
## Step 1: Run ESLint (ignoring test files)
```bash
cd frontend && npm.cmd run lint -- --ignore-pattern "*.test.js"
```

If there are warnings or errors:
1. Fix them immediately in the affected files
2. Re-run lint to verify fixes
3. Only then proceed to rebuild frontend container

## Common Issues to Watch For
- `no-unused-vars` - Remove unused imports, variables, or state
- `react-hooks/exhaustive-deps` - Add missing dependencies to useEffect
- Missing semicolons or syntax errors
