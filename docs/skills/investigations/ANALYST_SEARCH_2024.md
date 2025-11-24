# Domain-Specific Search Capability for All Analyst Agents

## Purpose

All 23 expert analyst agents have domain-specific search capability to enrich their analysis with current, authoritative sources.

## How Analysts Use WebSearch

When analyzing events, analysts should use the WebSearch tool to:

1. **Find Current Data**: Get latest statistics, research findings, reports
2. **Verify Facts**: Confirm details about events, policies, or phenomena
3. **Access Domain Resources**: Find scholarly articles, official reports, expert analyses
4. **Update Knowledge**: Access information beyond training cutoff date
5. **Enrich Analysis**: Add contemporary sources to strengthen evidence base

## Search Pattern for Each Analyst

### Economist Analyst

**Search for**:

- Economic data (GDP, unemployment, inflation rates)
- Policy details (fiscal stimulus amounts, tax rates, regulatory specifics)
- Market information (commodity prices, stock indices, exchange rates)
- Research papers (NBER working papers, academic studies)
- International data (World Bank, IMF, OECD statistics)

**Example searches**:

```
"US inflation rate 2025 Federal Reserve"
"Carbon tax British Columbia economic impact study"
"NBER working paper minimum wage employment effects"
```

### Political Scientist Analyst

**Search for**:

- Election results and polling data
- Treaty texts and diplomatic statements
- Institutional details (constitutions, electoral systems)
- Foreign policy documents
- Political science research (APSA journals, policy briefs)

**Example searches**:

```
"NATO Article 5 invocations historical precedents"
"Democratization success factors comparative study"
"APSR political institutions electoral systems"
```

### Historian Analyst

**Search for**:

- Primary source collections
- Historical scholarship (American Historical Review)
- Timeline details and chronologies
- Historiographical debates
- Archival resources

**Example searches**:

```
"Weimar Republic collapse primary sources"
"Industrial Revolution timeline Britain"
"American Historical Review comparative revolutions"
```

### Domain-Specific Patterns

**All analysts** should use WebSearch when they need:

- Current statistics or data
- Specific details about events
- Recent research findings
- Verification of facts
- Authoritative sources
- Contemporary context

## Integration with Analysis Process

Analysts should incorporate WebSearch at appropriate steps:

**Step 1: Define Event** - Search for event details, timeline, key facts

**Step 4-5: Apply Frameworks** - Search for data supporting analysis (elasticities, precedents, research findings)

**Step 7-8: Ground in Evidence** - Search for empirical studies, historical cases, authoritative sources

**Step 9: Synthesize** - Verify final claims with current sources

## Search Quality Standards

When using WebSearch, analysts should:

1. **Use Authoritative Sources**: Academic journals, government agencies, professional organizations
2. **Cite Sources**: Include links in analysis
3. **Current Data**: Prefer recent (2024-2025) when timeliness matters
4. **Domain-Appropriate**: Use discipline-specific databases and resources
5. **Multiple Sources**: Corroborate important claims

## Allowed Domains for Each Analyst

Analysts may use `allowed_domains` parameter to focus searches:

**Economist**: `aeaweb.org`, `nber.org`, `imf.org`, `worldbank.org`, `fred.stlouisfed.org`

**Political Scientist**: `apsanet.org`, `cambridge.org/core/journals/american-political-science-review`, `jstor.org`

**Environmental**: `nature.com`, `ipcc.ch`, `epa.gov`, `unep.org`

**And so on** for each domain's authoritative sources

## Example: Economist Using WebSearch

```
Analysis Task: Evaluate Federal Reserve interest rate decision

Step 1: Get current data
WebSearch: "Federal Reserve interest rate decision November 2025"
WebSearch: "US inflation rate October 2025 CPI"
WebSearch: "Federal Reserve dot plot 2025"

Step 4: Find supporting research
WebSearch: "Taylor Rule optimal interest rate 2025"
WebSearch: "NBER monetary policy effectiveness recent research"

Step 8: Verify empirical claims
WebSearch: "Historical Federal Reserve rate hikes recession probability"

Analysis Output:
"According to the Federal Reserve's November 2025 decision (source: federalreserve.gov),
the FOMC raised rates by 0.50%. Current inflation stands at 3.8% (BLS CPI October 2025).
Historical analysis (NBER WP 2024) suggests..."
```

## Enabling WebSearch in Skills

All analyst skills include WebSearch as an available tool through Claude Code's built-in capabilities. No special configuration required - analysts can simply use WebSearch as needed during analysis.

## Best Practices

1. **Search Early**: Get facts and data before deep analysis
2. **Verify Claims**: Use search to confirm empirical assertions
3. **Update Knowledge**: Access post-training information
4. **Preserve Links**: Include URLs in analysis output
5. **Domain-Focused**: Use allowed_domains to filter noise

---

**Status**: All 23 analyst agents have WebSearch capability
**Implementation**: Built into Claude Code, available by default
**Documentation**: This guidance added to analyst ecosystem
