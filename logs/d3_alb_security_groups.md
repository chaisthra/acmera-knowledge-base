# D3.2 ALB and Security Groups

## Q1. Health check path and target status

- Health check path: `/health`
- Target status: **Healthy** (1 target)

Found at: EC2 → Load Balancers → acmera-dev → Target groups → acmera-dev → Targets tab

---

## Q2. ALB listener port and forwarding

- ALB listens on **port 80 (HTTP)**
- Forwards traffic to target group `acmera-dev` on **port 8080** (the container port)

---

## Q3. ECS security group inbound rules

| Rule | Protocol | Port | Source |
|------|----------|------|--------|
| sgr-00ba22c22a418ace6 | TCP | 8080 | sg-0969179299fdbe2ea (ALBSecurityGroup) |

The source is the ALB security group ID rather than `0.0.0.0/0` because only the ALB should send traffic to the ECS tasks — no direct public access to containers. This is the principle of least privilege: if port 8080 were open to `0.0.0.0/0`, anyone could bypass the ALB and hit the container directly, bypassing any ALB-level rules, WAF, or rate limiting.

---

## Q4. RDS security group — can you connect from your laptop?

| Rule | Protocol | Port | Source |
|------|----------|------|--------|
| sgr-061881dd22f76165b | TCP | 5432 | sg-0e8ebc57f95351516 (ECSSecurityGroup) |

**Cannot connect directly from laptop** — only the ECS tasks (via ECSSecurityGroup) are allowed.

To allow laptop access, you would temporarily add your public IP (`x.x.x.x/32`) to the RDS security group on port 5432 — which was done during the one-time ingest run and then revoked immediately after.

This is a bad idea to leave open permanently because it exposes the database directly to the internet, making it vulnerable to brute-force attacks, credential stuffing, and exploits against the Postgres protocol itself.

---

## Q5. Adding HTTPS (port 443) to the ALB — what two things are needed?

1. **ACM Certificate** — an SSL/TLS certificate issued via AWS Certificate Manager (ACM) for your domain (e.g. `api.yourdomain.com`). ACM issues it free; you prove domain ownership via DNS or email validation.

2. **New HTTPS Listener** — add a port 443 listener to the ALB referencing the ACM certificate ARN, forwarding to the same target group. Also requires adding port 443 inbound to the ALB security group.
