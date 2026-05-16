# D3 RDS and Secrets Manager

## Q1. RDS Endpoint URL

```
<redacted>.ap-south-1.rds.amazonaws.com
```

Connection command:
```bash
psql "host=$RDSHOST port=5432 dbname=acmera_kb user=workshop sslmode=verify-full sslrootcert=./global-bundle.pem"
```

---

## Q2. Connecting to RDS from laptop

Direct connection does not work by default — the RDS security group only allows inbound port 5432 from the ECS security group, not from any external IP.

During the one-time ingest run, the laptop's public IP was temporarily added to the RDS security group, the ingest completed, and the rule was immediately revoked. This is the correct approach — open only when needed, close immediately after.

---

## Q3. RDS Query Editor in the Console

The RDS Query Editor requires an upgraded AWS account plan — it is not available on the free tier. Even if available, it would still require the database to accept connections from the console's IP, which is blocked by the security group (only ECS tasks are allowed).

---

## Q4. Secrets Manager — are values visible?

The secret values (`acmera/dev/db` and `acmera/dev/app`) are visible in the console when logged in as the root user or an IAM user with full Secrets Manager access.

In a production setup, access should be restricted via IAM — only the ECS TaskExecutionRole should have `secretsmanager:GetSecretValue` permission on these specific secrets. Other IAM users and roles should be explicitly denied or simply not granted access.

The IAM role that grants ECS permission to read secrets: `TaskExecutionRole` (defined in the CloudFormation stack), which has a policy allowing `secretsmanager:GetSecretValue` on `acmera/dev/db` and `acmera/dev/app`.

---

## Q5. What if OPENAI_API_KEY were committed as a plain env var in the task definition?

The key would be visible in plaintext to anyone with AWS Console access — visible under ECS → Task Definitions → Container definitions → Environment variables. Task definitions are also stored in CloudFormation and can appear in CloudTrail logs.

More critically, if the key were also committed to a git repository, it would be permanently in git history even if later deleted, and could be scraped by bots that scan public repos. This would allow anyone to use the API key, running up charges on the account until the key is rotated.

Using Secrets Manager means the task definition only stores a reference (`ValueFrom: arn:...`) — the actual key value is never visible in the ECS console or logs.

> Screenshot: Secrets Manager showing `acmera/dev/db` and `acmera/dev/app` with values hidden — [attach screenshot]
