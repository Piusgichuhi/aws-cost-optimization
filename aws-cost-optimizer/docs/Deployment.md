# Deployment Guide

A complete, step-by-step guide to deploying the AWS Cost Optimizer from scratch, with an explanation of every step. Follow it in order the first time, then use it as a reference.

## Contents

1. [What you are about to do](#1-what-you-are-about-to-do)
2. [Install the tools](#2-install-the-tools)
3. [Set up AWS access (IAM user and access keys)](#3-set-up-aws-access)
4. [Configure the AWS CLI](#4-configure-the-aws-cli)
5. [Build the project](#5-build-the-project)
6. [Deploy with SAM](#6-deploy-with-sam)
7. [Confirm the email subscription](#7-confirm-the-email-subscription)
8. [Test the function](#8-test-the-function)
9. [Go live (turn off dry-run)](#9-go-live)
10. [Update and redeploy](#10-update-and-redeploy)
11. [Tear everything down](#11-tear-everything-down)
12. [Troubleshooting](#12-troubleshooting)
13. [Security checklist](#13-security-checklist)

---

## 1. What you are about to do

Deploying means turning the code and `template.yaml` on your laptop into real running resources in your AWS account.

```
Your laptop                                   Your AWS account
-----------                                   ----------------
src/ (Python code)      sam build             packaged code
template.yaml        ----------------->       (.aws-sam/ folder)
                        sam deploy
                     ----------------->       CloudFormation stack
                     (uses your access        |- Lambda function
                      keys to prove           |- EventBridge schedule
                      who you are)            |- DynamoDB table
                                              |- SNS topic + email subscription
                                              '- IAM role for the Lambda
```

Three things make this work:

| Piece | Job |
|---|---|
| AWS CLI | Stores your credentials and talks to AWS |
| SAM CLI | Packages your code and deploys the template |
| Access keys | Prove to AWS that the commands come from you |

## 2. Install the tools

You need four tools. Check each one in a terminal (Command Prompt or PowerShell on Windows).

| Tool | Check command | What it is for |
|---|---|---|
| Git | `git --version` | Version control and pushing to GitHub |
| Python 3.12 | `python --version` | Runtime for the code and for local testing |
| AWS CLI v2 | `aws --version` | Credentials and AWS commands |
| AWS SAM CLI | `sam --version` | Build and deploy serverless apps |

If a command says "not recognized", install that tool, then open a new terminal window so the system picks up the change.

## 3. Set up AWS access

SAM makes API calls to AWS for you: it creates an S3 bucket, a CloudFormation stack, a Lambda function and so on. AWS accepts these calls only from an identified, authorized user. That identity is an access key pair.

### Why not use the root account?

The root user is the email address you signed up with. It has unlimited power and cannot be restricted. If its keys leak, an attacker can run up your bill or delete everything. Day-to-day work should use a limited IAM user instead.

### Create the IAM user

1. Sign in to the AWS Console and open IAM.
2. Go to Users, then Create user.
3. Name it `sam-deployer`. Do not enable console access. This user is for the command line only.
4. Choose Attach policies directly and select `AdministratorAccess`.
5. Click Next, then Create user.

`AdministratorAccess` is used here because the deploy creates IAM roles, tables, topics and buckets, and writing a minimal policy for that takes time. It is acceptable for a personal learning account. In a company, you would replace it with a custom least-privilege policy.

### Create the access key

1. Open the `sam-deployer` user and go to Security credentials.
2. Under Access keys, click Create access key.
3. Choose Command Line Interface (CLI), confirm, and create it.
4. You get two values:
   - Access key ID (starts with `AKIA`)
   - Secret access key (shown only once)
5. Download the `.csv` file and store it somewhere private.

> Treat the secret key like a password. Never put it in code, in a commit, in a screenshot, or in a chat message.

## 4. Configure the AWS CLI

```bash
aws configure
```

| Prompt | Enter |
|---|---|
| AWS Access Key ID | your `AKIA...` value |
| AWS Secret Access Key | your secret |
| Default region name | `us-east-1` |
| Default output format | `json` |

This writes two files in your user profile:

| File | Contents |
|---|---|
| `~/.aws/credentials` | the access key and secret |
| `~/.aws/config` | region and output format |

On Windows the folder is `C:\Users\<you>\.aws\`. It is outside your project folder, so your keys cannot be committed by accident.

### Verify it

```bash
aws sts get-caller-identity
```

Expected output is JSON containing your account number and an ARN ending in `user/sam-deployer`. This command answers the question "who does AWS think I am?" If it fails, fix credentials before going further.

## 5. Build the project

```bash
cd aws-cost-optimizer
sam build
```

What `sam build` does:

- Reads `template.yaml`
- Collects the code in `src/` and any dependencies
- Writes the result to a hidden `.aws-sam/` folder, which is what actually gets uploaded

Run `sam build` before every deploy. If you skip it, SAM deploys the previous build and your changes will not appear.

If it complains about the Python version, either install Python 3.12 or change the `Runtime` line in `template.yaml` to the version you have.

## 6. Deploy with SAM

```bash
sam deploy --guided
```

`--guided` asks questions and saves your answers to `samconfig.toml`. After the first time you only need `sam deploy`.

| Prompt | Recommended answer | What it means |
|---|---|---|
| Stack Name | `aws-cost-optimizer` | A stack is the bundle of resources CloudFormation manages. One name lets you update or delete them together |
| AWS Region | `us-east-1` | Where resources are created. The scanner only sees resources in this same region |
| Parameter AlertEmail | your email | Who receives the report |
| Parameter DryRun | `true` | Safe mode: scans and reports but never deletes |
| Confirm changes before deploy | `y` | Shows the planned changes and waits for your approval |
| Allow SAM CLI IAM role creation | `y` | Required. The Lambda needs an IAM role and SAM creates it |
| Disable rollback | `n` | With `n`, a failed deploy cleans itself up. With `y` you must delete the half-built stack before retrying |
| Save arguments to configuration file | `y` | Stores answers in `samconfig.toml` |
| SAM configuration file / environment | press Enter | Defaults are fine |
| Create managed S3 bucket (if asked) | `y` | SAM needs a bucket to upload your code package |

SAM then shows a change set listing the resources it will create. Type `y` to approve. Deployment takes one to three minutes and ends with a success message and stack outputs.

## 7. Confirm the email subscription

SNS sends a message titled "AWS Notification - Subscription Confirmation" to the address you provided. Open it (check spam) and click Confirm subscription. Until you do, no reports will be delivered. This step exists so nobody can subscribe your address without your consent.

## 8. Test the function

Find the function name:

```bash
aws lambda list-functions --query "Functions[].FunctionName" --output text
```

Invoke it:

```bash
aws lambda invoke --function-name <function-name> out.json
type out.json        # on macOS/Linux use: cat out.json
```

Expected output is a summary such as:

```json
{"found": 0, "flagged": 0, "cleaned": 0, "exempt": 0}
```

You should also receive the report by email. To see the tool find something:

1. In the EC2 console, create a 1 GB volume and do not attach it.
2. Invoke the function again.
3. The volume should appear in the report as flagged.

Remember to delete the test volume afterwards, since it costs a few cents per month.

To read the logs if something looks wrong:

```bash
sam logs --stack-name aws-cost-optimizer --tail
```

## 9. Go live

Only do this after several dry-run reports look correct.

```bash
sam deploy --parameter-overrides DryRun=false AlertEmail=you@example.com
```

Even live, nothing is touched until a resource has been flagged for longer than `GRACE_DAYS`, and exempt resources are always skipped.

## 10. Update and redeploy

After changing code or the template:

```bash
sam build
sam deploy
```

`sam deploy` reads `samconfig.toml`, so there are no questions the second time.

## 11. Tear everything down

```bash
sam delete
```

This removes the whole stack: Lambda, schedule, table, topic and role. Use it when you finish experimenting so nothing keeps running. Also consider deleting the `sam-deployer` access key in IAM when you no longer need it.

## 12. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Unable to locate credentials` | AWS CLI is not configured | Run `aws configure`, then `aws sts get-caller-identity` |
| `InvalidClientTokenId` or `SignatureDoesNotMatch` | Key or secret typed wrongly | Run `aws configure` again and re-enter carefully |
| `AccessDenied` | User lacks permissions | Check `AdministratorAccess` is attached to `sam-deployer` |
| `ROLLBACK_COMPLETE` or `CREATE_FAILED` | Stack failed to create | Read the error in the CloudFormation Events tab, run `sam delete`, fix, deploy again |
| Build fails on Python version | Runtime mismatch | Install Python 3.12 or change `Runtime` in `template.yaml` |
| `sam: command not found` | SAM CLI not installed or terminal not restarted | Install it, open a new terminal |
| No email arrives | Subscription unconfirmed or in spam | Check spam, click the confirmation link |
| Report shows nothing | Account has no waste, or wrong region | Create a test volume, or check the region matches |
| Code changes not showing | Forgot to rebuild | Run `sam build` before `sam deploy` |

## 13. Security checklist

- [ ] Root account has MFA enabled and is not used for daily work
- [ ] The deploy user has an access key that is stored privately, never in Git
- [ ] `.aws-sam/` and `samconfig.toml` are listed in `.gitignore`
- [ ] The key is deleted or deactivated when the project is finished
- [ ] `DryRun=true` until reports have been reviewed
- [ ] Test resources are deleted after testing