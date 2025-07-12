# CI/CD Setup Guide for DNS Proxy

## Difficulty: Easy to Medium

### Why It's EASY:
1. **Free GitHub Actions** works perfectly for this project
2. **2,000 minutes/month** free - more than enough
3. **Ubuntu runners** available (matches your Debian target)
4. **No API key needed** for public repos
5. **Simple YAML configuration**

### Why It's MEDIUM:
1. **Debian packaging** needs proper dependencies
2. **DNS testing** might need mocking
3. **Systemd testing** requires containers
4. **Network tests** need special handling

## Option 1: GitHub Actions (Recommended for Start)

### Pros:
- Zero setup cost
- Integrated with GitHub
- Great marketplace of actions
- Easy secret management

### Cons:
- Public visibility (unless private repo)
- Limited to GitHub infrastructure

### What You Get Free:
- 2,000 minutes/month
- 500MB storage
- 20 concurrent jobs
- Linux, Windows, macOS runners

## Option 2: GitLab CI (Your Local Server)

### Pros:
- Complete control
- Private/secure
- No minute limits
- Can use powerful local hardware

### Cons:
- Need to maintain runners
- More setup complexity

### GitLab CI Example:
```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

test:python:
  stage: test
  image: python:3.10
  script:
    - pip install -r requirements.txt
    - pytest

build:debian:
  stage: build
  image: debian:bookworm
  script:
    - apt-get update
    - apt-get install -y build-essential debhelper
    - dpkg-buildpackage -b -uc -us
  artifacts:
    paths:
      - ../*.deb
```

## Quick Start (5 Minutes):

1. **Choose the simple workflow**:
   ```bash
   git add .github/workflows/quick-test.yml
   git commit -m "ci: Add basic GitHub Actions workflow"
   git push
   ```

2. **Watch it run**:
   - Go to GitHub repo → Actions tab
   - See your tests run automatically!

3. **No secrets needed** for basic testing

## Advanced Setup (30 Minutes):

1. **Full test suite** with coverage
2. **Debian package building**
3. **Automatic releases**
4. **Security scanning**

## Testing Locally First:

```bash
# Install act (GitHub Actions locally)
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflows locally
act -j quick-test
```

## Gradual Approach:

### Phase 1: Basic Testing (Easy - 5 min)
- Syntax checking ✓
- Import testing ✓
- Basic unit tests ✓

### Phase 2: Full Testing (Easy - 15 min)
- All unit tests
- Integration tests
- Coverage reports

### Phase 3: Package Building (Medium - 30 min)
- Debian package build
- Package installation test
- Multi-version testing

### Phase 4: Release Automation (Medium - 45 min)
- Tag-based releases
- Automatic changelog
- Package publishing

## GitLab + GitHub Sync:

Since you have both:

```bash
# In your GitLab repo
git remote add github https://github.com/pshempel/no-ipv6-dns-proxy.git

# Push to both
git push origin main
git push github main
```

Or use GitLab's repository mirroring feature for automatic sync.

## Recommendation:

**Start with GitHub Actions** (quick-test.yml) because:
1. Zero infrastructure needed
2. See results in 5 minutes
3. Learn the basics quickly
4. Free tier is generous

Then gradually add more complex workflows as needed.

## Bottom Line:

- **Difficulty**: Easy for basics, Medium for full pipeline
- **Time to basic CI**: 5 minutes
- **Time to full CI/CD**: 2-3 hours
- **Maintenance**: Almost none for basic, minimal for full