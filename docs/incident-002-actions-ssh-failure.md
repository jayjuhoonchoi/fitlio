# Incident 002 — GitHub Actions SSH Authentication Failure

## Date
2026-05-18

## Symptoms
- GitHub Actions deploy job failing with `ssh: handshake failed`
- Test job passing, deploy job failing
- EC2 was reachable via manual SSH

## Root Causes (3 separate issues)
1. `EC2_HOST` Secret was empty
2. `appleboy/ssh-action` failed to parse the SSH private key format
3. `EC2_USER` Secret had a trailing whitespace (`ubuntu ` instead of `ubuntu`)

## Diagnosis Steps
1. Checked Actions log → found `dial tcp ***:22: i/o timeout`
2. Checked GitHub Secrets → EC2_HOST was empty
3. After filling EC2_HOST → new error: `ssh: no key found`
4. Replaced appleboy action with direct SSH command
5. Still failing → checked EC2_USER → found trailing whitespace

## Resolution
1. Filled all three Secrets: EC2_HOST, EC2_USER, EC2_SSH_KEY
2. Replaced `appleboy/ssh-action` with direct SSH command in deploy.yml
3. Removed trailing whitespace from EC2_USER

## Prevention
- After any Secret update, trigger a test deployment immediately
- Use direct SSH command instead of third-party action for better error messages
- Check ALL secrets, not just the one you think is wrong

## Lessons Learned
- `dial tcp: i/o timeout` = EC2_HOST wrong or unreachable
- `ssh: no key found` = key format issue
- `Permission denied (publickey)` = wrong user or key mismatch
- A single whitespace in a Secret value breaks everything