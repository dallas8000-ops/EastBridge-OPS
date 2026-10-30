# Domain & SSL Setup

Production URL: https://eastbridge.gilliomfrontlinedigital.com
Domain: eastbridge.gilliomfrontlinedigital.com
Framework: django

## SSL
SSL/TLS is automatic on Vercel, Railway, and Fly.io custom domains.

## Stripe Webhook (production)
Update webhook URL to: `https://eastbridge.gilliomfrontlinedigital.com/webhooks/stripe/`

## Verification
```bash
curl https://eastbridge.gilliomfrontlinedigital.com/health/
```
Run readiness from Stripe Installer after deploy.
