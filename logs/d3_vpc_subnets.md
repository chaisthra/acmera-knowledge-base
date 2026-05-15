# D3 VPC, Subnets, and NAT Gateway

## Q1. VPC CIDR block

`10.0.0.0/16`

---

## Q2. Subnet CIDR blocks

| Name | Type | CIDR |
|------|------|------|
| acmera-public-a | Public | 10.0.1.0/24 |
| acmera-public-b | Public | 10.0.2.0/24 |
| acmera-private-a | Private | 10.0.11.0/24 |
| acmera-private-b | Private | 10.0.12.0/24 |

---

## Q3. Which subnet each service lives in

| Service | Subnet | Type |
|---------|--------|------|
| ALB | subnet-02167772b6cd7b0d4 (ap-south-1a), subnet-0d6f110a2cfbca005 (ap-south-1b) | Public |
| ECS task | ap-south-1b (acmera-public-b) | Public |
| RDS | subnet-0e477e797cf9510a0 (acmera-private-b, ap-south-1b), subnet-0c1dcc0c6892697f0 (acmera-private-a, ap-south-1a) | Private |

---

## Q4. NAT Gateway

No NAT Gateway exists in this deployment. ECS tasks run in **public subnets** with `AssignPublicIp: ENABLED`, so they reach the internet (OpenAI API, Langfuse) directly via the Internet Gateway. This avoids the ~$32/month NAT Gateway cost for a dev environment.

In a production setup where ECS tasks would be in private subnets, a NAT Gateway would be required. Without it, tasks in private subnets have no outbound internet route — calls to the OpenAI API would time out because there is no path from the private subnet to the internet. The NAT Gateway sits in a public subnet, and private subnets route `0.0.0.0/0` traffic to it; the NAT Gateway then forwards packets to the internet using its own public IP.

---

## Q5. Architecture diagram

```
Internet
    │
    ▼
Internet Gateway
    │
    ▼
ALB (public subnets: 10.0.1.0/24, 10.0.2.0/24)
    │  port 80
    ▼
ECS Task (public subnet: 10.0.2.0/24)  ──► OpenAI API / Langfuse
    │  port 5432                              (direct via IGW, no NAT)
    ▼
RDS pgvector (private subnets: 10.0.11.0/24, 10.0.12.0/24)

─────────────────────────────────────────
Public subnets:  ALB, ECS tasks
Private subnets: RDS
NAT Gateway:     Not provisioned (dev setup — ECS uses public IP instead)
```

> Hand-drawn diagram: [attach photo]
