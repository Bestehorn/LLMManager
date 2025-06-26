# Security Policy

## Supported Versions

We currently support the following versions of bestehorn-llmmanager with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of bestehorn-llmmanager seriously. If you have discovered a security vulnerability in this project, please report it to us as described below.

### Reporting Process

1. **DO NOT** disclose the vulnerability publicly until it has been addressed by our team.

2. Email your findings to [markus.bestehorn@googlemail.com](mailto:markus.bestehorn@googlemail.com). Encrypt your findings using our PGP key to prevent this critical information from being read by third parties.

3. Provide the following information in your report:
   - Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
   - Full paths of source file(s) related to the manifestation of the issue
   - The location of the affected source code (tag/branch/commit or direct URL)
   - Any special configuration required to reproduce the issue
   - Step-by-step instructions to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact of the issue, including how an attacker might exploit the issue

### What to Expect

- We will acknowledge receipt of your vulnerability report within 48 hours
- We will send a more detailed response within 5 business days indicating the next steps in handling your report
- We will keep you informed of the progress towards a fix and full announcement
- We will credit you in the release notes (unless you prefer to remain anonymous)

### Security Update Process

1. The security team will investigate the vulnerability and determine its impact
2. Fixes will be prepared for all supported versions
3. On the embargo date, the fixes will be pushed to the public repository
4. Release announcements will be made on GitHub and PyPI

## Security Best Practices for Users

When using bestehorn-llmmanager, please follow these security best practices:

### Authentication

1. **Never hardcode credentials** in your source code
2. Use AWS IAM roles when running on EC2, ECS, or Lambda
3. Use AWS profiles for local development
4. Rotate credentials regularly
5. Apply the principle of least privilege to IAM policies

### Data Protection

1. **Validate all inputs** before sending to AWS Bedrock
2. **Sanitize outputs** from LLMs before using in your application
3. Be cautious with tool use configurations - validate tool inputs/outputs
4. Use guardrails when available for content filtering

### Network Security

1. Use TLS/SSL for all communications
2. Run in a VPC with appropriate security groups when possible
3. Monitor AWS CloudTrail logs for suspicious activity

### Dependency Management

1. Regularly update bestehorn-llmmanager and its dependencies
2. Use tools like `pip-audit` to check for known vulnerabilities
3. Pin dependencies in production environments

## Known Security Considerations

### LLM-Specific Risks

1. **Prompt Injection**: Always validate and sanitize user inputs before sending to LLMs
2. **Data Leakage**: Be cautious about what data you send to LLMs
3. **Hallucinations**: Don't trust LLM outputs for critical decisions without validation
4. **Tool Use**: Carefully validate any tool configurations and outputs

### AWS-Specific Considerations

1. **Region Selection**: Ensure you're using regions that comply with your data residency requirements
2. **Service Quotas**: Monitor usage to prevent denial of service
3. **Cost Management**: Set up billing alerts to prevent unexpected charges

## Security Features

bestehorn-llmmanager includes several security features:

1. **Request Validation**: All requests are validated before sending to AWS
2. **Response Validation**: Optional response validation with custom functions
3. **Error Handling**: Sensitive information is not exposed in error messages
4. **Secure Defaults**: Secure configuration defaults where possible
5. **Audit Logging**: Comprehensive logging for security monitoring

## Compliance

bestehorn-llmmanager is designed to work with AWS Bedrock, which provides:

- SOC 1, 2, and 3 compliance
- PCI DSS compliance
- ISO 27001, 27017, 27018, and 27701 certifications
- HIPAA eligibility
- GDPR compliance features

Please ensure your usage complies with your specific regulatory requirements.

## Resources

- [AWS Security Best Practices](https://aws.amazon.com/security/security-resources/)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [AWS Bedrock Security](https://docs.aws.amazon.com/bedrock/latest/userguide/security.html)

## Contact

For any security-related questions that are not vulnerabilities, please open an issue on GitHub with the "security" label.

Thank you for helping keep bestehorn-llmmanager and its users safe!
