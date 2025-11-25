# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of Source Atlas seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **quyennv.4work@gmail.com**

Include the following information:
- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: Within 7 days
  - High: Within 30 days
  - Medium: Within 90 days
  - Low: Next scheduled release

### What to Expect

1. **Acknowledgment**: We'll acknowledge receipt of your vulnerability report
2. **Validation**: We'll validate and reproduce the vulnerability
3. **Fix Development**: We'll develop a fix
4. **Disclosure**: We'll coordinate disclosure with you
5. **Credit**: We'll credit you in the security advisory (if desired)

## Security Best Practices

When using Source Atlas:

### Environment Variables

- **Never commit** `.env` files with real credentials
- Use strong, unique passwords for Neo4j
- Rotate credentials regularly
- Use environment-specific credentials (dev/staging/prod)

### Neo4j Security

```bash
# Use strong passwords
APP_NEO4J_PASSWORD=<strong-random-password>

# Use TLS in production
APP_NEO4J_URL=bolt+s://your-server:7687

# Limit network access
# Configure firewall rules to restrict Neo4j access
```

### Docker Security

```yaml
# Don't use default passwords in docker-compose
environment:
  - NEO4J_AUTH=neo4j/${SECURE_PASSWORD}
  
# Use secrets in production
secrets:
  neo4j_password:
    external: true
```

### Code Analysis Security

- Be cautious when analyzing untrusted code
- Run in isolated environments (containers) when possible
- Validate LSP server integrity
- Limit file system access

## Known Security Considerations

### LSP Servers

Source Atlas integrates with Language Server Protocol servers. Ensure:
- LSP servers are from trusted sources
- Servers are kept up to date
- Servers run with minimal privileges

### Code Execution

- Source Atlas does NOT execute analyzed code
- Tree-sitter only parses code statically
- No remote code execution vulnerabilities

### Data Storage

- Code chunks are stored in Neo4j
- Ensure Neo4j is properly secured
- Consider encryption at rest for sensitive codebases
- Review Neo4j access controls

## Security Updates

Security updates will be released as:
- Patch versions for minor issues
- Minor versions for significant issues  
- Announcements via GitHub Security Advisories

## Disclosure Policy

- We follow coordinated vulnerability disclosure
- We'll work with you to understand and fix the issue
- We'll publicly disclose once a fix is available
- We'll credit researchers (with permission)

## Security Hall of Fame

We appreciate security researchers who help keep Source Atlas secure:

- (No reports yet)

## Contact

For security concerns: quyennv.4work@gmail.com

For general issues: https://github.com/quyen-ngv/source-atlas/issues

---

Thank you for helping keep Source Atlas and our users safe! 🔒
