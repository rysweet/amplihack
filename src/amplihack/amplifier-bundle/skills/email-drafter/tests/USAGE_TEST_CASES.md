# Email Drafter Skill - Usage Test Cases

This document contains test cases to verify the email-drafter skill produces correct outputs for various combinations of tones and contexts.

## Test Case Format

Each test case includes:

- **Test ID**: Unique identifier
- **Tone**: One of (formal, casual, technical)
- **Context**: One of (status_update, request, announcement, follow_up, response, recap)
- **Input**: Bullet points or notes
- **Expected Characteristics**: What the output should demonstrate
- **Verification Steps**: How to verify correctness

---

## Tone Tests

### T1: Formal Tone Characteristics

**Test**: Formal tone is consistently applied across all contexts

**Characteristics to Verify**:

- Complete sentences with proper punctuation
- Formal salutations ("Dear", "Sincerely")
- Respectful language ("I would like", "Thank you for")
- Professional closing ("Best regards", "Respectfully")
- No contractions (don't → do not)
- Passive voice acceptable in formal contexts

### T2: Casual Tone Characteristics

**Test**: Casual tone is consistently applied across all contexts

**Characteristics to Verify**:

- Conversational language
- Informal salutations ("Hi", "Hey")
- Can use contractions (doesn't, can't, we'll)
- Friendly closings ("Thanks", "Cheers")
- Direct, friendly statements
- First-person perspective

### T3: Technical Tone Characteristics

**Test**: Technical tone is consistently applied across all contexts

**Characteristics to Verify**:

- Precise terminology
- Specific technical details
- Direct, unambiguous language
- Lists and structured information
- References to systems/specifications
- Clear technical specifications

---

## Context Tests

### C1: Status Update Structure

**Test**: Status update context produces appropriate structure

**Input Elements**:

- Completed work items
- In-progress items
- Upcoming tasks
- Potential blockers

**Expected Structure**:

1. Opening statement about what period/project
2. Completed section with accomplishments
3. In-progress section
4. Upcoming section
5. Issues/blockers (if mentioned)
6. Closing with invitation for discussion

### C2: Request Structure

**Test**: Request context produces appropriate structure

**Input Elements**:

- What is being asked
- Why it matters
- Timeline/deadline
- Resource needs

**Expected Structure**:

1. Context/background
2. Clear specific request
3. Rationale/importance
4. Timeline and deliverables
5. Next steps/how to respond
6. Appreciation/closing

### C3: Announcement Structure

**Test**: Announcement context produces appropriate structure

**Input Elements**:

- The announcement/news
- Why it matters
- How it affects recipients
- Any actions needed

**Expected Structure**:

1. Lead with the announcement
2. Context and rationale
3. Details and specifics
4. Impact on recipients
5. Required actions/next steps
6. Contact for questions

### C4: Follow-up Structure

**Test**: Follow-up context produces appropriate structure

**Input Elements**:

- Previous conversation reference
- Updates since conversation
- Actions needed next
- Items for confirmation

**Expected Structure**:

1. Reference previous conversation
2. Summary of decisions made
3. Update on progress
4. Next steps and ownership
5. Timeline for future interaction
6. Closing confirmation

### C5: Response Structure

**Test**: Response context produces appropriate structure

**Input Elements**:

- Question/inquiry being answered
- Direct answer
- Supporting details
- Next steps if applicable

**Expected Structure**:

1. Appreciation for reaching out
2. Direct answer to question
3. Supporting details/explanation
4. Actionable next steps
5. Offer of additional help
6. Professional closing

### C6: Recap Structure

**Test**: Recap context produces appropriate structure

**Input Elements**:

- What was discussed
- Decisions made
- Action items with owners
- Deadlines
- Outstanding items

**Expected Structure**:

1. Opening (what was discussed)
2. Decisions section
3. Action items (who, what, when)
4. Outstanding/unresolved issues
5. Next meeting/touchpoint
6. Closing

---

## Combined Tone + Context Tests

### TC1: Formal Status Update

**Input**:

- Tone: formal
- Context: status_update
- Content: Weekly project progress

**Verification**:

- Uses formal greeting/closing
- Clear section headers (Completed Items, In Progress, Upcoming)
- Professional language throughout
- Complete sentences with proper punctuation

### TC2: Casual Request

**Input**:

- Tone: casual
- Context: request
- Content: Budget request for training

**Verification**:

- Friendly but professional tone
- Conversational language
- Clear what's being requested
- Informal closing appropriate to casual tone

### TC3: Technical Announcement

**Input**:

- Tone: technical
- Context: announcement
- Content: System architecture change

**Verification**:

- Technical terminology appropriate
- Precise specifications included
- Direct language
- Technical details clearly explained

### TC4: Formal Follow-up

**Input**:

- Tone: formal
- Context: follow_up
- Content: Post-meeting confirmation

**Verification**:

- Formal language throughout
- References previous meeting
- Clear action items with ownership
- Professional closing

### TC5: Casual Response

**Input**:

- Tone: casual
- Context: response
- Content: Answer to technical question

**Verification**:

- Casual, friendly tone
- Direct answer to question
- Helpful without being overly formal
- Informal closing

### TC6: Technical Recap

**Input**:

- Tone: technical
- Context: recap
- Content: Architecture review summary

**Verification**:

- Technical precision
- Clear decisions documented
- Specific action items
- Proper technical language

---

## Quality Tests

### Q1: Grammar and Punctuation

**Test**: Generated emails have no grammar or punctuation errors

**Verification Steps**:

- Check all sentences have proper punctuation
- Verify subject-verb agreement
- Confirm proper comma usage
- Verify no spelling errors

### Q2: Tone Consistency

**Test**: Tone remains consistent throughout email

**Verification Steps**:

- Opening tone matches closing
- No unexpected shifts in formality
- Language level consistent
- Voice (first/second/third person) consistent

### Q3: Clarity and Readability

**Test**: Email is clear and easy to understand

**Verification Steps**:

- Main point is obvious
- Key information is highlighted
- Logical flow from section to section
- Action items are clear (if any)

### Q4: Appropriate Length

**Test**: Email length is appropriate for context

**Verification Steps**:

- Concise but complete (not too short, not too long)
- All important information included
- No unnecessary repetition
- Proper use of white space and formatting

### Q5: Professional Formatting

**Test**: Email follows professional formatting standards

**Verification Steps**:

- Appropriate paragraph breaks
- Lists properly formatted (bullets/numbers)
- Headers/sections clearly labeled
- Salutation and closing are appropriate

---

## Edge Cases

### E1: Multiple Action Items

**Input**: Status update with 5+ action items

**Expected**: Action items clearly numbered/listed with owners and dates

### E2: Complex Technical Content

**Input**: Technical context with specialized terminology

**Expected**: Technical language is precise and accurate without being obscure

### E3: Emotional Sensitivity

**Input**: Difficult news or sensitive topic

**Expected**: Tone remains professional while showing appropriate sensitivity

### E4: Competing Priorities

**Input**: Multiple priorities or conflicting messages

**Expected**: Email clearly prioritizes and structures competing information

### E5: Very Bullet-Heavy Input

**Input**: 20+ bullet points

**Expected**: Organized into logical sections without being overwhelming

---

## Manual Verification Checklist

For each generated email, verify:

- [ ] Tone is consistent with requested tone
- [ ] Structure matches requested context
- [ ] Grammar and punctuation are correct
- [ ] No spelling errors
- [ ] Action items are clear (if applicable)
- [ ] Appropriate length
- [ ] Professional formatting
- [ ] Main message is clear
- [ ] Logical flow from section to section
- [ ] Greeting and closing are appropriate
- [ ] No unnecessary jargon (unless technical tone)
- [ ] Reads naturally (not robotic)

---

## Success Criteria

The skill successfully generates emails when:

1. **Tone Accuracy**: Generated email demonstrates requested tone consistently
2. **Context Appropriateness**: Structure and approach match requested context
3. **Content Preservation**: All key information from input is included
4. **Quality Standards**: Email meets professional communication standards
5. **Readability**: Email is clear, well-organized, and easy to understand
6. **Professional Standards**: Grammar, punctuation, formatting are all correct

All test cases pass when generated emails meet these criteria.
