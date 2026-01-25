# Work IQ Usage Examples

Real-world examples of using Work IQ to query Microsoft 365 data.

## Email Examples

### Find Emails by Sender

```
User: "What did John say about the proposal?"

Work IQ: Found 3 emails from John about the proposal:

1. RE: Q4 Proposal Review
   From: John Smith
   Date: Yesterday
   Preview: "I've reviewed the Q4 numbers and have concerns about..."

2. Proposal Updates Needed
   From: John Smith
   Date: 3 days ago
   Preview: "After the client meeting, we need to revise..."
```

### Search by Subject

```
User: "Find emails about budget approval"

Work IQ: Found 5 emails matching 'budget approval':

1. RE: Q1 Budget Approval - APPROVED
2. Budget Approval Process Update
3. Action Required: Budget Approval
...
```

### Filter by Time

```
User: "Show me emails from last week about the project deadline"

Work IQ: Found 8 emails from last week about project deadline...
```

### Find Unread Important Emails

```
User: "What unread emails do I have from my manager?"

Work IQ: You have 2 unread emails from Sarah Chen:

1. Action Required: Review before Friday
2. Team restructuring announcement
```

### Search Sent Items

```
User: "What did I send to the client about pricing?"

Work IQ: Found 3 emails you sent about pricing:

1. To: client@example.com
   Subject: Updated Pricing Proposal
   Sent: Monday
```

## Calendar & Meeting Examples

### View Today's Schedule

```
User: "What meetings do I have today?"

Work IQ: You have 3 meetings today:

1. 9:00 AM - Daily Standup (15 min, Teams)
2. 11:00 AM - Design Review (1 hr, Room A)
3. 3:00 PM - 1:1 with Manager (30 min, Teams)
```

### Check Tomorrow

```
User: "What's on my calendar tomorrow?"

Work IQ: Tomorrow's schedule:

1. 10:00 AM - Sprint Planning (2 hrs)
2. 2:00 PM - Client Demo (1 hr)
```

### Find Past Meetings

```
User: "When did we last meet about the API redesign?"

Work IQ: Found meeting "API Redesign Discussion"
- Date: Last Tuesday, 2:00 PM
- Attendees: You, Alex, Marcus, Sarah
- Duration: 1 hour
```

### Check Specific Day

```
User: "What meetings do I have next Tuesday?"

Work IQ: Next Tuesday's schedule:
1. 9:30 AM - Architecture Review
2. 1:00 PM - Product Sync
3. 4:00 PM - Retrospective
```

### Find Recurring Meetings

```
User: "Show my weekly team meetings"

Work IQ: Weekly recurring meetings:

1. Monday 9:00 AM - Weekly Standup
2. Wednesday 2:00 PM - Team Sync
3. Friday 4:00 PM - Week Review
```

## Teams Message Examples

### Search Channel Messages

```
User: "What did the team discuss about the deployment?"

Work IQ: Found discussions in #engineering channel:

- Alex: "Deployment scheduled for Friday 10 PM"
- Sarah: "Do we have rollback plan ready?"
- Marcus: "Rollback tested and documented"
```

### Find Specific Person's Messages

```
User: "Show me what Alex said in Teams about the security audit"

Work IQ: Messages from Alex about security audit:

1. In #security channel:
   "Audit results came back - 2 medium issues to address"

2. In direct chat:
   "Can you help with the remediation plan?"
```

### Summarize Channel Activity

```
User: "Summarize today's messages in the Engineering channel"

Work IQ: Today's #engineering activity:

- 15 messages, 6 participants
- Main topics: deployment prep, code review, testing
- Action items: Deploy at 10 PM, review PR #234
```

### Find Shared Links

```
User: "Find links shared in #project-alpha channel"

Work IQ: Recent links in #project-alpha:

1. Design doc: https://sharepoint.com/doc/...
2. Figma mockups: https://figma.com/file/...
3. Requirements: https://sharepoint.com/req/...
```

## Document Search Examples

### Find Recent Documents

```
User: "Find my recent PowerPoint presentations"

Work IQ: Found 4 PowerPoint files modified recently:

1. Q4 Review.pptx - Modified yesterday
2. Product Roadmap 2026.pptx - Modified 3 days ago
3. Architecture Overview.pptx - Modified last week
```

### Search by Content

```
User: "Find documents containing 'microservices architecture'"

Work IQ: Found 8 documents:

1. Architecture Decision Record.docx
   Match: "...microservices architecture provides..."

2. Technical Design.pdf
   Match: "...migrating to microservices architecture..."
```

### Find Documents by Author

```
User: "Show documents Sarah shared with me"

Work IQ: Documents shared by Sarah:

1. Budget Planning.xlsx - Can edit
2. Project Timeline.mpp - Can view
3. Requirements Spec.docx - Can edit
```

### Search Specific Location

```
User: "Find Excel files in the Engineering folder"

Work IQ: Excel files in /Engineering/:

1. Sprint Metrics.xlsx
2. API Performance.xlsx
3. Test Results.xlsx
```

## Workflow Patterns

### Morning Email Triage

```
1. "Show unread emails from last 12 hours"
2. "Find emails from my manager this week"
3. "What action items are in my recent emails?"
```

### Meeting Preparation

```
1. "Show my 2 PM meeting details"
2. "Find emails about the project we're discussing"
3. "Show notes from our last meeting on this topic"
```

### Project Context Gathering

```
1. "Find all emails about Project Phoenix"
2. "Show meetings about Phoenix from last month"
3. "Search Teams in #phoenix channel"
4. "Find documents containing 'Phoenix'"
```

### End-of-Week Review

```
1. "Show my meetings from this week"
2. "What documents did I create this week?"
3. "Show Teams messages where I was mentioned"
```

### Code Review Context

```
1. "Find emails from Alex about the auth module"
2. "Search Teams for auth implementation discussions"
3. "Show the architecture decision document"
```

### Incident Response

```
1. "Find Teams messages in #incidents from last 2 hours"
2. "Show emails about deployment this week"
3. "Find the deployment runbook document"
```

## Tips for Effective Queries

### Be Specific

✅ **Good:** "Find emails from Sarah about the Q4 budget"
❌ **Vague:** "Show me emails"

### Use Time Ranges

✅ **Good:** "Meetings this week with the design team"
❌ **Broad:** "All my meetings"

### Combine Filters

✅ **Good:** "Unread emails from last week about deadlines"
❌ **Single filter:** "Unread emails" (may be too many)

### Ask Follow-ups

```
First: "Find emails about the API project"
Then: "Show me the most recent one"
Then: "What attachments were in that email?"
```

---

**Related Documentation:**

- [SKILL.md](./SKILL.md) - Overview and quick start
- [reference.md](./reference.md) - Technical reference

**Last Updated:** 2026-01-23
