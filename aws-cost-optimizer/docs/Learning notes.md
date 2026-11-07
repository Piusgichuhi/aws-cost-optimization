# Learning Notes

Plain-language notes on the concepts I learned while building this project. These are written to be re-read later, so every term is explained from first principles.

## Contents

1. [What is AWS SAM](#1-what-is-aws-sam)
2. [What is CloudFormation](#2-what-is-cloudformation)
3. [SAM vs CloudFormation vs clicking in the console](#3-sam-vs-cloudformation-vs-clicking-in-the-console)
4. [Anatomy of template.yaml](#4-anatomy-of-templateyaml)
5. [SAM commands cheat sheet](#5-sam-commands-cheat-sheet)
6. [What is a stack](#6-what-is-a-stack)
7. [Credentials, IAM and access keys](#7-credentials-iam-and-access-keys)
8. [How the AWS CLI finds credentials](#8-how-the-aws-cli-finds-credentials)
9. [IAM roles vs IAM users](#9-iam-roles-vs-iam-users)
10. [Least privilege](#10-least-privilege)
11. [Region](#11-region)
12. [Dry-run and grace period design](#12-dry-run-and-grace-period-design)
13. [Why Lambda needs DynamoDB for memory](#13-why-lambda-needs-dynamodb-for-memory)
14. [Lessons learned: the credentials error](#14-lessons-learned-the-credentials-error)
15. [Glossary](#15-glossary)

---

## 1. What is AWS SAM

SAM stands for Serverless Application Model. It is a toolkit made of two parts:

- A template format: a shorter way to describe serverless resources (Lambda functions, schedules, tables) in a YAML file.
- A command-line tool (`sam`): builds, tests and deploys that template.

The problem it solves: creating a Lambda function, its permissions, its schedule, a database and a notification topic by clicking in the console takes dozens of steps, is easy to get wrong, and cannot be repeated exactly. SAM lets me describe everything once in a file and deploy it with two commands.

## 2. What is CloudFormation

CloudFormation is the AWS service that actually creates resources from a template. This is the engine, and SAM is a friendlier layer on top.

When I run `sam deploy`:

1. SAM converts my short template into a full CloudFormation template (this is the `Transform: AWS::Serverless-2016-10-31` line).
2. It uploads my code to S3.
3. It asks CloudFormation to create or update the resources.
4. CloudFormation creates them in the right order and rolls back if something fails.

The idea behind it all is called Infrastructure as Code (IaC): infrastructure described in files that live in Git, can be reviewed, versioned and recreated at will.

## 3. SAM vs CloudFormation vs clicking in the console

| Approach | Repeatable | Reviewable in Git | Effort for serverless |
|---|---|---|---|
| Console clicking | No | No | High, error-prone |
| Raw CloudFormation | Yes | Yes | Verbose (hundreds of lines) |
| SAM | Yes | Yes | Short (about 60 lines for this project) |

A single SAM line such as `Type: Schedule` replaces an EventBridge rule, a target and a Lambda permission that raw CloudFormation would need separately.

## 4. Anatomy of template.yaml

```yaml
AWSTemplateFormatVersion: "2010-09-09"      # CloudFormation version, always this value
Transform: AWS::Serverless-2016-10-31       # tells AWS "expand SAM shortcuts"

Parameters:                                  # values asked at deploy time
  AlertEmail: {Type: String}
  DryRun: {Type: String, Default: "true"}

Resources:                                   # the things to create
  StateTable:                                # DynamoDB table
  ReportTopic:                               # SNS topic with email subscription
  OptimizerFunction:                         # Lambda + its role + its schedule
```

| Section | Purpose |
|---|---|
| `Parameters` | Inputs (email, dry-run flag) so the template is reusable |
| `Resources` | Everything to create |
| `Properties` | Settings for each resource |
| `Environment: Variables` | Values the Python code reads with `os.environ` |
| `Policies` | The permissions the Lambda's IAM role receives |
| `Events: Schedule` | The EventBridge cron trigger |
| `!Ref` | Refers to another resource or parameter by name |
| `!GetAtt` | Reads an attribute (like a topic's name) from a resource |

## 5. SAM commands cheat sheet

| Command | What it does | When to use |
|---|---|---|
| `sam build` | Packages the code into `.aws-sam/` | Before every deploy |
| `sam deploy --guided` | Interactive first deploy, saves answers | First time |
| `sam deploy` | Deploys using saved answers | Every later time |
| `sam delete` | Deletes the whole stack | Cleanup |
| `sam logs --tail` | Streams the Lambda logs | Debugging |
| `sam validate` | Checks the template for errors | Before committing |
| `sam local invoke` | Runs the function locally in Docker | Fast testing |

## 6. What is a stack

A stack is one CloudFormation deployment: a named group of resources managed as a single unit. My stack contains the Lambda, schedule, table, topic and role.

- Updating the template and redeploying changes only what differs.
- Deleting the stack deletes all the resources inside it.
- If creation fails halfway, CloudFormation rolls back, so I never end up with half a system.

This is why `sam delete` is a clean way to stop all costs.

## 7. Credentials, IAM and access keys

Every call to AWS must answer two questions:

- Authentication: who are you?
- Authorization: are you allowed to do this?

IAM (Identity and Access Management) answers both.

| Term | Meaning |
|---|---|
| Root user | The account owner (the signup email). Unlimited power, should not be used daily |
| IAM user | A separate identity with chosen permissions |
| Policy | A JSON document that lists allowed or denied actions |
| Access key ID | The "username" part of programmatic credentials (starts with `AKIA`) |
| Secret access key | The "password" part. Shown once, must be kept private |

My laptop talks to AWS using the access key of an IAM user (`sam-deployer`). The key is how AWS knows the request is mine.

## 8. How the AWS CLI finds credentials

When I run `aws` or `sam`, the tools look in this order and use the first match:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. The shared credentials file (`~/.aws/credentials`), written by `aws configure`
3. Other sources such as SSO or an attached IAM role (on EC2 or Lambda)

If none of those exist, the result is the error I hit: `Unable to locate credentials`.

Useful check: `aws sts get-caller-identity` shows which identity the tools are currently using.

## 9. IAM roles vs IAM users

| | IAM user | IAM role |
|---|---|---|
| Used by | A person or a program outside AWS | An AWS service (like Lambda) or a temporary session |
| Credentials | Long-lived access keys | Temporary, rotated automatically |
| In this project | `sam-deployer` on my laptop | The Lambda's execution role |

The Lambda function never has an access key. When it runs, AWS gives it temporary credentials through its role. That is safer, because there is no secret stored in code that could leak.

## 10. Least privilege

The principle: give every identity only the permissions it needs and nothing more.

| Identity | Permissions | Why |
|---|---|---|
| `sam-deployer` (me) | `AdministratorAccess` | Convenient for learning in a personal account. Too broad for production |
| Lambda role | Only EC2 describe/cleanup, CloudWatch read, one DynamoDB table, one SNS topic | If the code were ever compromised, the damage is limited |

Next improvement: replace `AdministratorAccess` on the deploy user with a custom policy that covers only what SAM needs.

## 11. Region

An AWS Region is a physical location with its own set of data centers (for example `us-east-1` in Virginia, `eu-west-1` in Ireland). Resources exist inside one region.

Consequences for this project:

- The stack is created in the region chosen at deploy time.
- The scanner only sees EBS volumes, IPs and instances in that same region.
- To audit other regions, deploy the stack there or extend the code to loop over regions.

## 12. Dry-run and grace period design

Automation that deletes things needs layers of safety. This project uses:

| Safety layer | How it protects |
|---|---|
| Dry-run flag | Reports only, takes no action |
| Grace period | A resource must stay flagged for N days before action |
| Exemption tag | `cost-optimizer=exempt` permanently protects a resource |
| Stop instead of terminate | Idle EC2 instances can be restarted |
| Auto-clear | If someone fixes the resource, the flag is removed |
| Audit trail | Every cleanup is recorded with a timestamp |

Design principle: make the safe path the default, and require a deliberate change to enable destructive behavior.

## 13. Why Lambda needs DynamoDB for memory

A Lambda function is stateless. Each run starts fresh, with no memory of the previous run, and its local disk is discarded. But the grace-period logic needs to know "when did I first see this volume?"

DynamoDB solves that by storing, per resource:

- `resource_id` (the key)
- `status` (`flagged`, `exempt`, `deleted`)
- `first_seen` (the grace-period clock)
- `deleted_at` (audit)

General lesson: serverless functions are stateless, so persistent state belongs in a database.

## 14. Lessons learned: the credentials error

What happened: I ran `sam deploy --guided` and answered all the questions. It stopped at "Looking for resources needed for deployment" with:

```
Error: Unable to locate credentials
```

Why: SAM needed to call AWS to create a deployment bucket, but my computer had no access keys configured, so AWS had no way to know who I was.

How I fixed it:

1. Created an IAM user (`sam-deployer`) instead of using the root account.
2. Created an access key for it.
3. Ran `aws configure` to store the key locally.
4. Verified with `aws sts get-caller-identity`.
5. Re-ran `sam build` and `sam deploy --guided`.

What I learned:

- Deploy tools run on my machine but act inside my AWS account, so they need credentials.
- Credentials live in `~/.aws/`, outside the project, which keeps them out of Git.
- `aws sts get-caller-identity` is the first diagnostic for any AWS permission problem.
- Errors that happen before any resource is created are safe: nothing was deployed.
- Never use the root account's keys for daily work.

## 15. Glossary

| Term | Meaning |
|---|---|
| ARN | Amazon Resource Name, a unique ID for any AWS resource |
| CLI | Command-line interface |
| Cron | A schedule expression, for example `cron(0 6 * * ? *)` means 06:00 UTC daily |
| Change set | A preview of what CloudFormation will create, update or delete |
| Dry-run | A mode that reports what would happen without doing it |
| FinOps | Managing and optimizing cloud spending |
| Grace period | Waiting time before an automatic action is taken |
| IaC | Infrastructure as Code |
| IAM | Identity and Access Management |
| Idempotent | Safe to run repeatedly with the same result |
| Orphaned resource | A resource that is not attached to or used by anything |
| Pagination | Fetching large result sets page by page from an API |
| Region | A geographic AWS location with its own data centers |
| Rollback | Undoing a failed deployment automatically |
| SAM | Serverless Application Model |
| Serverless | Running code without managing servers |
| Stack | A named group of resources deployed together by CloudFormation |
| Stateless | Retains no memory between runs |
| Topic (SNS) | A channel that messages are published to and subscribers receive from |