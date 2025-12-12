# Email Drafter Skill

Professional email generation from bullet points and conversation summaries.

## Quick Start

Use the email-drafter skill whenever you need to:
- Convert meeting notes into formal communications
- Draft professional requests
- Create team announcements
- Write follow-up emails
- Respond to inquiries professionally
- Summarize meetings with action items

## Skill Invocation

Provide Claude with:
1. **Content**: Your bullet points or notes
2. **Tone**: One of (formal, casual, technical)
3. **Context**: One of (status_update, request, announcement, follow_up, response, recap)
4. **Optional**: Recipient details, specific requirements

Example usage:

```
Please use the email-drafter skill to help me write an email.

Tone: formal
Context: status_update

Content:
- Completed user authentication system
- Achieved 94% test coverage
- API endpoints optimized, 15% faster
- Database migration testing underway
- Need approval on new schema design
```

## Skill Files

- **SKILL.md** - Complete skill documentation with all supported tones and contexts
- **README.md** - This file, quick reference guide
- **tests/USAGE_TEST_CASES.md** - Test cases for verifying correct output

## Features

### Three Tones

| Tone | Use For | Language | Greeting |
|------|---------|----------|----------|
| **Formal** | Executives, external stakeholders, important announcements | Professional, complete sentences, respectful | "Dear [Name]" |
| **Casual** | Teammates, internal communications, collaborative contexts | Friendly, conversational, approachable | "Hi [Name]" |
| **Technical** | Technical teams, specifications, domain experts | Precise, detailed, industry terminology | "Hello [Team]" or direct opening |

### Six Contexts

1. **status_update** - Progress reports, weekly updates, sprint reviews
2. **request** - Budget requests, approvals, resource needs
3. **announcement** - News, policy changes, team updates
4. **follow_up** - Post-meeting follow-ups, action confirmation
5. **response** - Answers to inquiries, replies to questions
6. **recap** - Meeting summaries, decision documentation

## Generated Email Characteristics

Every generated email includes:
- Appropriate greeting for the tone
- Clear, logical structure
- Professional formatting
- Proper punctuation and grammar
- Relevant section headers
- Appropriate sign-off and closing

## Philosophy

This skill embodies amplihack principles:
- **Ruthless Simplicity**: Pure text transformation, no dependencies
- **Self-Contained**: Works independently, needs no external services
- **Professional Output**: Generates production-ready content
- **Immediate Usability**: Every email is ready to send (review first!)

## What This Skill Does

✓ Converts bullet points to structured emails
✓ Applies consistent tone throughout
✓ Organizes information appropriately
✓ Ensures professional formatting
✓ Handles multiple contexts and audiences

## What This Skill Does NOT Do

✗ Send emails on your behalf
✗ Change the meaning of your content
✗ Add information you didn't provide
✗ Override your requested tone
✗ Generate inappropriate content

**Always review generated emails before sending.** You remain responsible for accuracy and appropriateness.

## Tips for Best Results

1. **Be Specific**: Provide concrete details rather than vague statements
2. **Highlight Priorities**: Mark important items if information is extensive
3. **Clarify Action Items**: Specify who should do what and by when
4. **Provide Context**: Help Claude understand why information matters
5. **Consider Audience**: Mention if recipients are executives, teammates, or external parties

## Examples

### Quick Example: Status Update (Formal)

Input:
```
Tone: formal
Context: status_update
Content:
- Completed API integration
- All tests passing (96% coverage)
- Performance improved 20%
- Need database review before deployment
```

Output:
```
Dear Team,

I am writing to provide an update on the API integration project.

Completed Items:
The API integration has been successfully completed with all tests passing. Code coverage has reached 96%, ensuring comprehensive validation.

Progress:
Performance improvements of 20% have been achieved through optimization efforts.

Pending Items:
The deployment is ready pending a comprehensive database review. Your input on the database configuration would be appreciated.

Please let me know if you have any questions.

Best regards,
[Your Name]
```

## Documentation

For complete documentation including:
- All supported tones with detailed characteristics
- All supported contexts with example structures
- Six comprehensive examples (one per context)
- Professional formatting guidelines
- Tips for specific use cases

See **SKILL.md** (main documentation file).

## Testing

Test cases are available in `tests/USAGE_TEST_CASES.md`:
- Tone consistency tests
- Context structure tests
- Combined tone + context tests
- Quality and grammar tests
- Edge case handling

Manual verification checklist is included for validating generated emails.

## Directory Structure

```
email-drafter/
├── README.md                           # This file
├── SKILL.md                            # Complete documentation
└── tests/
    └── USAGE_TEST_CASES.md             # Test cases and verification
```

## Integration

This skill is designed to work seamlessly with Claude Code as a Claude Skill. No installation required - use it directly in conversations with Claude.

## Support

If generated emails don't meet your needs:
1. Review the tone and context selected
2. Provide more specific content details
3. Clarify any special requirements
4. Consider the intended audience

See SKILL.md for detailed guidance on all supported combinations.

---

**Version**: 1.0
**Last Updated**: November 8, 2025
**Status**: Production Ready
