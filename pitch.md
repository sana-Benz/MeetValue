# MeetValue — Pitch

> **"This meeting could have been an email."**
> Everyone has thought it. MeetValue puts a price tag on it — *before* the invite goes out — and uses AI to tell you exactly who doesn't need to be there.

**Live app:** http://meetcost-frontend-022076688911.s3-website-us-east-1.amazonaws.com
**Category:** Workplace Efficiency · **Lane:** Startups

---

## The problem: meetings are the most expensive thing nobody budgets for

A meeting is never "free". Every attendee's salary keeps running for every minute, but that cost shows up on no calendar invite and no budget line. And the data says a large share of it is wasted:

- **$25,000 per employee per year.** That is how much companies spend on meetings their own employees consider unnecessary, out of an estimated **$80,000** per professional employee per year spent on meeting attendance. For a 100-person company, cutting that waste would save **nearly $2.5M a year**, and over **$100M** for a 5,000-person company. *(Otter.ai × Dr. Steven Rogelberg, UNC Charlotte, survey of 632 employees across 20+ industries, 2022)*
- **18 hours a week in meetings, 5.7 of them skippable.** Employees average 17.7 meetings a week. By their own account, 5.3 of those meetings could have been skipped *as long as they were kept in the loop*. They want to decline 31% of meetings but actually decline only 14%. *(same study)*
- **72% of meetings are ineffective**, and **78%** of knowledge workers say they are expected to attend so many meetings that it is hard to get their actual work done. **80%** say most of their meetings could be done in half the time. *(Atlassian, survey of 5,000 knowledge workers across 4 continents, 2024)*
- **71% of senior managers** say meetings are unproductive and inefficient, and **65%** say meetings keep them from completing their own work. *(Perlow, Hadley & Eun, "Stop the Meeting Madness", Harvard Business Review, 2017, survey of 182 senior managers)*

The waste isn't just *too many* meetings. It's **the wrong people in the room for the wrong amount of time.** Rogelberg's finding is the key one: employees can identify meetings they could skip, provided they are kept in the loop. They don't skip them, because nobody makes the cost visible and nobody gives them permission.

## Proof that showing the cost works: Shopify

In 2023, Shopify built an internal **meeting cost calculator** into Google Calendar. It estimated that a 30-minute meeting with three employees costs **$700 to $1,600**, and a one-hour meeting with seven people including two C-suite executives costs **$2,115**. Alongside a calendar purge that cancelled **12,000 recurring events**, Shopify projected cutting **322,000 hours** and **474,000 meetings** in 2023.

The lesson: **making meeting cost visible can become a concrete mechanism for challenging unnecessary meetings.** But Shopify built that tool for itself, using company-wide average compensation. Most teams don't have an engineering org to build one.

## Why existing meeting cost calculators aren't enough

Meeting cost calculators already exist, and they answer one question: *"how much does this meeting cost?"* Most of them stop there, with three limits:

1. **One flat rate for everyone.** Many calculators multiply attendees × duration × an average hourly rate. A junior developer and a VP get the same price, so the number is wrong exactly where it matters most.
2. **No notion of role.** Even when seniority is accounted for, a person's *job* isn't. A calculator can tell you the VP is expensive, but it can't tell you whether the VP *should be there*.
3. **No next step.** A big number is alarming, but it doesn't tell you what to change. "Invite fewer people" isn't advice.

## What MeetValue does differently

MeetValue answers the second question, the one that saves money: **"what should we change about this meeting?"**

| | Typical cost calculator | **MeetValue** |
|---|---|---|
| Cost per attendee | One average rate | **Per-person seniority rate, individually overridable** |
| Knows each attendee's role | ✗ | **✓ (e.g. "Backend Developer", "VP Sales")** |
| Judges relevance of each attendee to the meeting subject | ✗ | **✓ via AI** |
| Concrete recommendations | ✗ | **✓ partial attendance, shorter duration, consolidation** |
| Dollar savings per recommendation | ✗ | **✓ computed by the app, not guessed by the AI** |

**1. Cost that reflects who is actually in the room.** Each attendee has a seniority level (Junior, Mid, Senior, Executive) with a default hourly rate you can override. The result is a headline number, e.g. *"This meeting costs your company $650"*, with a per-person breakdown.

**2. AI recommendations that reason about relevance, not just price.** The meeting subject, each attendee's role and seniority, and the cost go to **Claude Haiku 4.5 on Amazon Bedrock**. The model is explicitly asked whether each person's *expertise* is relevant to the *subject*. Cost alone is the wrong signal: a $400/hr executive whose expertise is the whole point of the meeting shouldn't be cut, while a $50/hr developer sitting silently through a sales strategy review probably should be.

A real response from the live app, for a 60-minute *"Q4 sales pipeline review"* with a VP Sales, a Senior Account Executive and a Junior Backend Developer ($650 total):

> **Partial attendance — save $50:** *"Bob is a Backend Developer whose technical expertise is not relevant to a Q4 sales pipeline review… He should be removed from this meeting."*
>
> **Duration reduction — save $162.50:** *"The core participants have sufficient seniority and direct responsibility for pipeline management to conduct an efficient, focused review… A 15-minute reduction is achievable."*

That is Rogelberg's "could have skipped if kept in the loop" finding, turned into a specific, named, priced suggestion.

**3. Trustworthy numbers.** The AI decides *who* and *what*. The app computes the savings deterministically from the real hourly rates, so the dollar figures never depend on a model doing arithmetic. And if the AI is unavailable, the cost breakdown is still shown.

## Impact

- **For employees:** an objective, non-confrontational reason to skip a meeting and ask for the notes instead. Not "I don't want to come", but "the tool says my time is better spent elsewhere."
- **For managers:** a pre-flight check before sending an invite. Ten seconds to see the price and the leanest version of the meeting.
- **For companies:** even capturing a fraction of the **$25,000 per employee per year** in unnecessary meeting time pays back many times over. Recovering one unnecessary hour-long meeting a week for a single mid-level employee at $100/hr is about **$5,000 a year**.

## Where it's headed

MeetValue is built as the first step of a product, not a one-off demo:

- **Calendar integration (Google Calendar / Outlook):** show the cost and the AI suggestions *inside* the invite flow, at the exact moment the decision is made. This is the natural freemium upsell: free standalone calculator, paid calendar-integrated version per team.
- **One-click "apply and recalculate":** accept a suggestion (drop an attendee, cut 15 minutes) and watch the number update live.
- **Team meeting spend over time:** "Your team spent $X on meetings this month, and $Y of it was flagged as avoidable." That's a recurring reason to come back, and a metric managers can report on.
- **Org-aware rates:** import real compensation bands per role from HR systems instead of default seniority rates.

**Business model:** freemium SaaS, priced per team. The target is the same buyer Shopify's experiment proved exists, at every company that can't build the tool in-house.

## Built on AWS, shipped with a coding agent

Serverless and pay-per-use, with no idle cost: **Amazon S3** (static frontend) → **Amazon API Gateway** → two **AWS Lambda** functions (Python 3.12) → **Amazon Bedrock** (Claude Haiku 4.5 via a cross-region inference profile), all defined in **AWS SAM**. Each Lambda has its own least-privilege IAM role. Built with **Kiro** using spec-driven development (requirements → design → tasks). Kiro also ran the deployment and debugging against the live AWS account. See the [README](README.md#how-it-was-built) for the full build story.

---

## Sources

- Otter.ai & Dr. Steven G. Rogelberg (UNC Charlotte), *The Cost of Unnecessary Meeting Attendance*, 2022: [report (PDF)](https://go.otter.ai/hubfs/Report_The%20Cost%20of%20Unnecessary%20Meeting%20Attendance.pdf) · [Inc. coverage](https://www.inc.com/ali-donaldson/otterai-meetings-productivity.html)
- Atlassian, *Workplace Woes: Meetings*, 2024: [atlassian.com](https://www.atlassian.com/blog/workplace-woes-meetings)
- Perlow, Hadley & Eun, *Stop the Meeting Madness*, Harvard Business Review, July–August 2017: [hbr.org](https://hbr.org/2017/07/stop-the-meeting-madness)
- Shopify meeting cost calculator: [Fortune / Yahoo Finance, interview with CFO Jeff Hoffmeister](https://finance.yahoo.com/news/shopify-cfo-explains-meeting-cost-105829140.html) · [CNN](https://www.cnn.com/2023/07/12/tech/shopify-meeting-cost-calculator)
