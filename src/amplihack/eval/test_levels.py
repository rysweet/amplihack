"""Test level definitions for progressive evaluation.

Each level represents increasing cognitive complexity:
- L1: Single source, direct recall
- L2: Multi-source synthesis
- L3: Temporal reasoning
- L4: Procedural learning
- L5: Contradiction handling
- L6: Incremental learning

Philosophy: Data-driven test definition, separates test content from runner logic.
"""

from dataclasses import dataclass


@dataclass
class TestArticle:
    """A test article/source."""

    title: str
    content: str
    url: str
    published: str
    metadata: dict | None = None


@dataclass
class TestQuestion:
    """A test question with expected answer."""

    question: str
    expected_answer: str
    level: str  # L1, L2, etc.
    reasoning_type: str  # e.g., "direct_recall", "cross_source_synthesis"


@dataclass
class TestLevel:
    """Complete test level definition."""

    level_id: str
    level_name: str
    description: str
    articles: list[TestArticle]
    questions: list[TestQuestion]
    requires_temporal_ordering: bool = False
    requires_update_handling: bool = False


# LEVEL 1: Baseline - Single Source Direct Recall
LEVEL_1 = TestLevel(
    level_id="L1",
    level_name="Single Source Direct Recall",
    description="Simplest test - direct fact retrieval from one source",
    articles=[
        TestArticle(
            title="2026 Winter Olympics Medal Update - February 15",
            content=(
                "As of February 15, 2026, the Milan-Cortina Winter Olympics medal standings show: "
                "Norway leads with 26 total medals (12 gold, 8 silver, 6 bronze). "
                "Italy is in second place with 22 total medals (8 gold, 7 silver, 7 bronze). "
                "The United States has 17 medals (5 gold, 6 silver, 6 bronze). "
                "Germany has 14 medals (4 gold, 5 silver, 5 bronze). "
                "Sweden has 11 medals (3 gold, 4 silver, 4 bronze). "
                "The Games continue through February 21, 2026."
            ),
            url="https://olympics.example.com/2026/medals/feb15",
            published="2026-02-15T18:00:00Z",
        )
    ],
    questions=[
        TestQuestion(
            question="How many total medals does Norway have as of February 15?",
            expected_answer="26 total medals (12 gold, 8 silver, 6 bronze)",
            level="L1",
            reasoning_type="direct_recall",
        ),
        TestQuestion(
            question="Which country is in second place?",
            expected_answer="Italy with 22 total medals",
            level="L1",
            reasoning_type="direct_recall",
        ),
        TestQuestion(
            question="When do the 2026 Winter Olympics end?",
            expected_answer="February 21, 2026",
            level="L1",
            reasoning_type="direct_recall",
        ),
    ],
)


# LEVEL 2: Multi-Source Synthesis
LEVEL_2 = TestLevel(
    level_id="L2",
    level_name="Multi-Source Synthesis",
    description="Requires combining information from multiple articles",
    articles=[
        TestArticle(
            title="2026 Winter Olympics Medal Standings - February 15",
            content=(
                "As of February 15, Norway leads the 2026 Milan Winter Olympics with 26 total medals and 12 golds. "
                "Italy is second with 22 medals and 8 golds. The United States has 17 medals with 5 golds. "
                "Germany has 14 medals with 4 golds. Sweden has 11 medals with 3 golds."
            ),
            url="https://olympics.example.com/2026/standings-feb15",
            published="2026-02-15T18:00:00Z",
        ),
        TestArticle(
            title="Individual Athlete Achievements at Milan 2026",
            content=(
                "Johannes Klaebo of Norway won his 9th career Olympic gold medal in the cross-country skiing relay event. "
                "Federica Brignone of Italy won the giant slalom gold at her home Olympics, a historic achievement. "
                "Lisa Vittozzi of Italy captured the biathlon pursuit gold medal with a stunning performance. "
                "Femke Kok of the Netherlands set an Olympic record of 36.49 seconds in the 500m speed skating event."
            ),
            url="https://olympics.example.com/2026/athletes",
            published="2026-02-15T20:00:00Z",
        ),
        TestArticle(
            title="Historical Context of Milan-Cortina 2026",
            content=(
                "The 2026 Winter Olympics in Milan-Cortina are the first Winter Olympics held in Italy since the 1956 Cortina Games, "
                "marking a 70-year gap. Italy's current tally of 8 gold medals already surpasses their previous best performance of "
                "5 gold medals achieved at the 2006 Turin Games. Norway continues their tradition as the all-time leader in "
                "Winter Olympic medals, with their Milan 2026 performance reinforcing this dominance."
            ),
            url="https://olympics.example.com/2026/history",
            published="2026-02-14T12:00:00Z",
        ),
    ],
    questions=[
        TestQuestion(
            question="How does Italy's 2026 gold medal performance compare to their previous best?",
            expected_answer="Italy has 8 golds in 2026, surpassing their previous best of 5 golds from 2006 Turin",
            level="L2",
            reasoning_type="cross_source_synthesis",
        ),
        TestQuestion(
            question="Which country's individual athletes won the most medals mentioned in the athlete achievements article?",
            expected_answer="Italy with 2 athletes mentioned (Federica Brignone and Lisa Vittozzi)",
            level="L2",
            reasoning_type="cross_source_synthesis",
        ),
        TestQuestion(
            question="What makes the 2026 Olympics historically significant for Italy?",
            expected_answer="First Winter Olympics in Italy since 1956 (70-year gap) and Italy already exceeded their previous best gold medal count",
            level="L2",
            reasoning_type="cross_source_synthesis",
        ),
    ],
)


# LEVEL 3: Temporal Reasoning
LEVEL_3 = TestLevel(
    level_id="L3",
    level_name="Temporal Reasoning",
    description="Requires tracking changes over time and computing differences",
    articles=[
        TestArticle(
            title="Medal Standings After Day 7 - February 13",
            content=(
                "After Day 7 of competition (February 13), Norway leads with 18 total medals and 8 golds. "
                "Italy has 14 total medals and 5 golds. The United States has 12 medals and 4 golds. "
                "Germany has 10 medals and 3 golds."
            ),
            url="https://olympics.example.com/2026/day7",
            published="2026-02-13T20:00:00Z",
            metadata={"day": 7},
        ),
        TestArticle(
            title="Medal Standings After Day 9 - February 15",
            content=(
                "After Day 9 of competition (February 15), Norway has 26 total medals and 12 golds. "
                "Italy has 22 total medals and 8 golds. The United States has 17 medals and 5 golds. "
                "Germany has 14 medals and 4 golds."
            ),
            url="https://olympics.example.com/2026/day9",
            published="2026-02-15T20:00:00Z",
            metadata={"day": 9},
        ),
        TestArticle(
            title="Medal Standings After Day 10 - February 16",
            content=(
                "After Day 10 of competition (February 16), Norway has 28 total medals and 13 golds. "
                "Italy has 24 total medals and 9 golds. The United States has 19 medals and 6 golds. "
                "Germany has 15 medals and 5 golds."
            ),
            url="https://olympics.example.com/2026/day10",
            published="2026-02-16T20:00:00Z",
            metadata={"day": 10},
        ),
    ],
    questions=[
        TestQuestion(
            question="How many medals did Norway win between Day 7 and Day 9?",
            expected_answer="8 medals (from 18 to 26)",
            level="L3",
            reasoning_type="temporal_difference",
        ),
        TestQuestion(
            question="Which country improved their gold medal count the most from Day 7 to Day 10?",
            expected_answer="Norway improved most with +5 golds (8 to 13), followed by Italy +4 (5 to 9) and US +2 (4 to 6)",
            level="L3",
            reasoning_type="temporal_comparison",
        ),
        TestQuestion(
            question="Describe the trend in Italy's gold medal performance over the three days",
            expected_answer="Italy showed acceleration: +3 golds Day 7-9, then +1 gold Day 9-10, gaining 4 golds total",
            level="L3",
            reasoning_type="temporal_trend",
        ),
    ],
    requires_temporal_ordering=True,
)


# LEVEL 4: Procedural Learning
LEVEL_4 = TestLevel(
    level_id="L4",
    level_name="Procedural Learning",
    description="Learning and applying step-by-step procedures",
    articles=[
        TestArticle(
            title="Complete Flutter Development Setup Guide",
            content=(
                "Setting up a Flutter development environment follows these steps:\n\n"
                "Step 1: Install Flutter SDK by downloading from flutter.dev and adding to PATH.\n"
                "Step 2: Verify installation by running 'flutter doctor' to check all dependencies.\n"
                "Step 3: Create a new project with 'flutter create my_app'.\n"
                "Step 4: Navigate to project directory with 'cd my_app'.\n"
                "Step 5: Run the app with 'flutter run' (requires emulator or physical device).\n"
                "Step 6: Edit lib/main.dart to customize your application.\n"
                "Step 7: Add dependencies to pubspec.yaml under the dependencies section.\n"
                "Step 8: Run 'flutter pub get' to install the dependencies.\n"
                "Step 9: Test your code with 'flutter test'.\n\n"
                "Common issues:\n"
                "- If flutter doctor shows issues with Android SDK, install Android Studio.\n"
                "- If you see version conflicts, run 'flutter upgrade' first.\n"
                "- If pub get fails, try 'flutter pub cache repair'.\n"
                "- For iOS development, you need Xcode installed (macOS only)."
            ),
            url="https://flutter-guide.example.com/setup-2026",
            published="2026-02-10T10:00:00Z",
        )
    ],
    questions=[
        TestQuestion(
            question="What command creates a new Flutter project?",
            expected_answer="flutter create my_app (or flutter create <project_name>)",
            level="L4",
            reasoning_type="procedural_recall",
        ),
        TestQuestion(
            question="What should you do if flutter doctor shows version conflicts?",
            expected_answer="Run 'flutter upgrade' first",
            level="L4",
            reasoning_type="procedural_troubleshooting",
        ),
        TestQuestion(
            question="Describe the complete workflow from creating a project to running tests",
            expected_answer=(
                "1. flutter create my_app, 2. cd my_app, 3. edit lib/main.dart, "
                "4. add dependencies to pubspec.yaml, 5. flutter pub get, 6. flutter test"
            ),
            level="L4",
            reasoning_type="procedural_sequence",
        ),
        TestQuestion(
            question="If I want to create a project called 'weather_app' and add the http package, what exact commands would I run?",
            expected_answer=(
                "1. flutter create weather_app, 2. cd weather_app, "
                "3. Add 'http: ^1.0.0' to pubspec.yaml dependencies, 4. flutter pub get"
            ),
            level="L4",
            reasoning_type="procedural_application",
        ),
    ],
)


# LEVEL 5: Contradiction Handling
LEVEL_5 = TestLevel(
    level_id="L5",
    level_name="Contradiction Handling",
    description="Detecting and reasoning about conflicting information",
    articles=[
        TestArticle(
            title="Record Viewership for 2026 Winter Olympics Opening Ceremony",
            content=(
                "The 2026 Winter Olympics opening ceremony in Milan was watched by an estimated 1.2 billion viewers worldwide, "
                "according to preliminary data from the International Olympic Committee. This makes it the most-watched Winter Olympics "
                "opening ceremony in history, surpassing the previous record of 900 million viewers for the 2022 Beijing Games. "
                "The ceremony featured spectacular performances showcasing Italian culture and technology."
            ),
            url="https://olympic-news-a.example.com/viewership-record",
            published="2026-02-08T09:00:00Z",
        ),
        TestArticle(
            title="Milan 2026 Opening Ceremony Viewership Analysis",
            content=(
                "Viewership data for the 2026 Milan Olympics opening ceremony compiled by independent media analysts shows "
                "approximately 800 million viewers tuned in globally. This represents a decline from the 2022 Beijing Games which "
                "attracted 900 million viewers. The decrease is attributed to changing viewing habits and increased fragmentation "
                "across streaming platforms. However, digital engagement metrics showed record social media interactions during the event."
            ),
            url="https://media-analytics.example.com/olympics-2026",
            published="2026-02-09T14:00:00Z",
        ),
    ],
    questions=[
        TestQuestion(
            question="How many people watched the 2026 opening ceremony?",
            expected_answer=(
                "There are conflicting reports: IOC estimates 1.2 billion viewers, "
                "while independent analysts report 800 million viewers"
            ),
            level="L5",
            reasoning_type="contradiction_detection",
        ),
        TestQuestion(
            question="Why might the two sources disagree about viewership numbers?",
            expected_answer=(
                "Different measurement methodologies (IOC preliminary data vs independent analysts), "
                "different counting methods (traditional TV only vs including streaming), "
                "or different time windows measured"
            ),
            level="L5",
            reasoning_type="contradiction_reasoning",
        ),
        TestQuestion(
            question="Which viewership figure would you consider more reliable and why?",
            expected_answer=(
                "Independent analysts (800M) may be more reliable because they explicitly mention methodology "
                "and account for fragmentation across platforms, while IOC figure is 'preliminary' and may have "
                "organizational bias toward reporting higher numbers"
            ),
            level="L5",
            reasoning_type="source_credibility",
        ),
    ],
)


# LEVEL 6: Incremental Learning
LEVEL_6 = TestLevel(
    level_id="L6",
    level_name="Incremental Learning",
    description="Update knowledge when new information arrives",
    articles=[
        TestArticle(
            title="Johannes Klaebo Makes Olympic History - February 15",
            content=(
                "As of February 15, 2026, Johannes Klaebo has won 9 Olympic gold medals, making him the most decorated "
                "Winter Olympian in history. The Norwegian cross-country skier achieved this milestone after winning the "
                "team relay event. His previous record was 8 golds, which he shared with Bjørn Dæhlie. Klaebo still has "
                "one more event remaining: the individual sprint on February 17."
            ),
            url="https://olympics.example.com/klaebo-record-feb15",
            published="2026-02-15T17:00:00Z",
            metadata={"phase": "initial"},
        ),
        TestArticle(
            title="Klaebo Extends Record with 10th Gold - February 17",
            content=(
                "Update: On February 17, 2026, Johannes Klaebo won his 10th Olympic gold medal in the individual sprint event, "
                "extending his own record as the most decorated Winter Olympian ever. The victory was particularly dominant, "
                "with Klaebo finishing 2.3 seconds ahead of his nearest competitor. This caps off an extraordinary Olympics for "
                "the 29-year-old Norwegian, who now has 10 golds across three Olympic Games (2018, 2022, 2026)."
            ),
            url="https://olympics.example.com/klaebo-10th-gold",
            published="2026-02-17T16:30:00Z",
            metadata={"phase": "update"},
        ),
    ],
    questions=[
        TestQuestion(
            question="How many Olympic gold medals does Johannes Klaebo have?",
            expected_answer="10 Olympic gold medals (as of February 17, 2026)",
            level="L6",
            reasoning_type="incremental_update",
        ),
        TestQuestion(
            question="How did Klaebo's record change between February 15 and February 17?",
            expected_answer="Increased from 9 to 10 golds after winning the individual sprint on February 17",
            level="L6",
            reasoning_type="incremental_tracking",
        ),
        TestQuestion(
            question="Describe Klaebo's complete Olympic achievement trajectory",
            expected_answer=(
                "Tied record at 8 golds with Bjørn Dæhlie, broke record with 9th gold in relay (Feb 15), "
                "extended record to 10 golds in sprint (Feb 17). Has competed across 3 Olympics (2018, 2022, 2026)"
            ),
            level="L6",
            reasoning_type="incremental_synthesis",
        ),
    ],
    requires_update_handling=True,
)


# LEVEL 7: Teacher-Student Knowledge Transfer
LEVEL_7 = TestLevel(
    level_id="L7",
    level_name="Teacher-Student Knowledge Transfer",
    description="Teacher agent learns content, teaches student agent, student answers questions",
    articles=[
        # Reuse L2 articles - rich, multi-source content good for teaching
        TestArticle(
            title="2026 Winter Olympics Medal Standings - February 15",
            content=(
                "As of February 15, Norway leads the 2026 Milan Winter Olympics with 26 total medals and 12 golds. "
                "Italy is second with 22 medals and 8 golds. The United States has 17 medals with 5 golds. "
                "Germany has 14 medals with 4 golds. Sweden has 11 medals with 3 golds."
            ),
            url="https://olympics.example.com/2026/standings-feb15",
            published="2026-02-15T18:00:00Z",
        ),
        TestArticle(
            title="Individual Athlete Achievements at Milan 2026",
            content=(
                "Johannes Klaebo of Norway won his 9th career Olympic gold medal in the cross-country skiing relay event. "
                "Federica Brignone of Italy won the giant slalom gold at her home Olympics, a historic achievement. "
                "Lisa Vittozzi of Italy captured the biathlon pursuit gold medal with a stunning performance. "
                "Femke Kok of the Netherlands set an Olympic record of 36.49 seconds in the 500m speed skating event."
            ),
            url="https://olympics.example.com/2026/athletes",
            published="2026-02-15T20:00:00Z",
        ),
        TestArticle(
            title="Historical Context of Milan-Cortina 2026",
            content=(
                "The 2026 Winter Olympics in Milan-Cortina are the first Winter Olympics held in Italy since the 1956 Cortina Games, "
                "marking a 70-year gap. Italy's current tally of 8 gold medals already surpasses their previous best performance of "
                "5 gold medals achieved at the 2006 Turin Games. Norway continues their tradition as the all-time leader in "
                "Winter Olympic medals, with their Milan 2026 performance reinforcing this dominance."
            ),
            url="https://olympics.example.com/2026/history",
            published="2026-02-14T12:00:00Z",
        ),
    ],
    questions=[
        TestQuestion(
            question="How many total medals does Norway have in the 2026 Olympics?",
            expected_answer="26 total medals (12 gold)",
            level="L7",
            reasoning_type="knowledge_transfer_recall",
        ),
        TestQuestion(
            question="Which Italian athletes won gold medals at the 2026 Olympics?",
            expected_answer="Federica Brignone (giant slalom) and Lisa Vittozzi (biathlon pursuit)",
            level="L7",
            reasoning_type="knowledge_transfer_recall",
        ),
        TestQuestion(
            question="How does Italy's 2026 performance compare to their previous best?",
            expected_answer="Italy has 8 golds in 2026, surpassing their previous best of 5 golds from 2006 Turin",
            level="L7",
            reasoning_type="knowledge_transfer_synthesis",
        ),
        TestQuestion(
            question="What makes the 2026 Olympics historically significant for Italy?",
            expected_answer="First Winter Olympics in Italy since 1956 (70-year gap) and Italy exceeded their previous best gold medal count",
            level="L7",
            reasoning_type="knowledge_transfer_synthesis",
        ),
    ],
)


# LEVEL 8: Metacognition - Agent reasoning about its own reasoning
# Based on MUSE framework (arXiv 2024) and Dunlosky & Metcalfe (2009)
LEVEL_8 = TestLevel(
    level_id="L8",
    level_name="Metacognition",
    description="Agent evaluates its own confidence and identifies knowledge gaps",
    articles=[
        TestArticle(
            title="2026 Winter Olympics Medal Standings - February 15",
            content=(
                "As of February 15, Norway leads the 2026 Milan Winter Olympics with 26 total medals and 12 golds. "
                "Italy is second with 22 medals and 8 golds. The United States has 17 medals with 5 golds. "
                "Germany has 14 medals with 4 golds. Sweden has 11 medals with 3 golds."
            ),
            url="https://olympics.example.com/2026/standings-feb15",
            published="2026-02-15T18:00:00Z",
        ),
    ],
    questions=[
        TestQuestion(
            question="How confident should you be in answering 'How many medals does Canada have?'",
            expected_answer=(
                "Low confidence - the provided information only covers Norway, Italy, US, Germany, "
                "and Sweden. Canada is not mentioned in the data, so I cannot answer this accurately."
            ),
            level="L8",
            reasoning_type="confidence_calibration",
        ),
        TestQuestion(
            question="What additional information would you need to determine if Norway will finish with the most golds?",
            expected_answer=(
                "I would need: remaining events and their schedules, which countries are competing "
                "in remaining events, and current form/rankings of athletes in those events. The data "
                "only shows standings as of Feb 15, not projections."
            ),
            level="L8",
            reasoning_type="gap_identification",
        ),
        TestQuestion(
            question="Which of these questions can you answer with HIGH confidence and which with LOW: "
            "(a) How many golds does Norway have? (b) Why does Norway have the most medals? "
            "(c) Will Italy finish second?",
            expected_answer=(
                "(a) HIGH confidence - directly stated: 12 golds. "
                "(b) LOW confidence - the data shows they lead but doesn't explain why. "
                "(c) LOW confidence - the data is a snapshot from Feb 15, cannot predict final standings."
            ),
            level="L8",
            reasoning_type="confidence_discrimination",
        ),
    ],
)


# LEVEL 9: Causal Reasoning - "Why did X happen?"
# Based on Pearl's causal hierarchy (2009) and Gopnik's "Theory Theory"
LEVEL_9 = TestLevel(
    level_id="L9",
    level_name="Causal Reasoning",
    description="Identifying causal chains and mechanisms from correlated observations",
    articles=[
        TestArticle(
            title="Italy's Record-Breaking Olympic Performance Analysis",
            content=(
                "Italy's 8 gold medals at the 2026 Milan Games represent their best Winter Olympics performance. "
                "Several factors contributed: (1) Home advantage - Italian athletes competed before supportive crowds, "
                "which sports psychology research shows can improve performance by 3-5%. "
                "(2) Investment in winter sports infrastructure increased 40% after winning the bid in 2019. "
                "(3) The Italian ski federation hired 12 new international coaches in 2023. "
                "(4) Federica Brignone, who won giant slalom gold, attributed her success to a new training "
                "program developed specifically for the Cortina course. "
                "(5) Italy had their worst Olympics in 2018 PyeongChang (3 golds) which triggered a complete "
                "restructuring of their winter sports program."
            ),
            url="https://olympics.example.com/2026/italy-analysis",
            published="2026-02-16T10:00:00Z",
        ),
    ],
    questions=[
        TestQuestion(
            question="What caused Italy to improve from 3 golds in 2018 to 8 golds in 2026?",
            expected_answer=(
                "A chain of causes: Poor 2018 result (3 golds) triggered program restructuring, "
                "which led to 40% increased infrastructure investment and hiring 12 international coaches "
                "in 2023. Home advantage (3-5% performance boost) and course-specific training also contributed."
            ),
            level="L9",
            reasoning_type="causal_chain",
        ),
        TestQuestion(
            question="If Italy had not won the 2026 hosting bid, would they still have won 8 golds?",
            expected_answer=(
                "Likely not. Without the hosting bid: (1) no home advantage (3-5% boost gone), "
                "(2) possibly less infrastructure investment (the 40% increase was linked to hosting), "
                "(3) no course-specific training for Cortina. However, the 2018 program restructuring "
                "and new coaches might still have improved their count above 3 golds."
            ),
            level="L9",
            reasoning_type="counterfactual_causal",
        ),
        TestQuestion(
            question="Which single factor was most important for Italy's improvement?",
            expected_answer=(
                "The program restructuring after 2018 was likely the root cause, as it triggered "
                "the infrastructure investment and coaching hires. Without the 2018 failure, the "
                "other changes wouldn't have happened. Home advantage amplified the effect but "
                "wasn't the root cause."
            ),
            level="L9",
            reasoning_type="root_cause_analysis",
        ),
    ],
)


# LEVEL 10: Counterfactual Reasoning - "What if X didn't happen?"
# Based on Byrne (2005) and nearest possible world constraint
LEVEL_10 = TestLevel(
    level_id="L10",
    level_name="Counterfactual Reasoning",
    description="Reasoning about hypothetical alternatives and their consequences",
    articles=[
        TestArticle(
            title="Johannes Klaebo's Dominance at Milan 2026",
            content=(
                "Johannes Klaebo won 3 individual gold medals at Milan 2026 (sprint, skiathlon, 50km), "
                "plus 1 relay gold, giving him 4 golds at these Games alone. His total career Olympic "
                "golds reached 10 across 3 Olympics. The Norwegian cross-country team collectively won "
                "8 of the 12 available cross-country golds. Without Klaebo, Norway would have won only "
                "4 cross-country golds based on the silver medalists' nationalities (2 Russian, 1 Swedish, "
                "1 Finnish). Norway's overall gold count of 13 would have dropped to 9 without Klaebo's "
                "individual golds (keeping the relay gold since the team might still have won)."
            ),
            url="https://olympics.example.com/2026/klaebo-dominance",
            published="2026-02-18T12:00:00Z",
        ),
        TestArticle(
            title="2026 Winter Olympics Final Medal Count",
            content=(
                "Final 2026 medal standings: Norway 30 total (13 gold), Italy 26 total (9 gold), "
                "Germany 18 total (6 gold), United States 20 total (6 gold), Sweden 14 total (4 gold). "
                "Cross-country skiing produced the most Norwegian golds (8 of 13). Alpine skiing "
                "produced the most Italian golds (4 of 9)."
            ),
            url="https://olympics.example.com/2026/final-standings",
            published="2026-02-22T10:00:00Z",
        ),
    ],
    questions=[
        TestQuestion(
            question="If Klaebo had not competed at Milan 2026, would Norway still have led the gold medal count?",
            expected_answer=(
                "Without Klaebo's 3 individual golds (keeping relay), Norway drops from 13 to 9-10 golds. "
                "Italy had 9 golds. So it would have been very close - Norway might have tied or slightly "
                "led Italy. Klaebo was the decisive margin in Norway's gold medal dominance."
            ),
            level="L10",
            reasoning_type="counterfactual_removal",
        ),
        TestQuestion(
            question="What if Italy had won the hosting bid for 2030 instead of 2026?",
            expected_answer=(
                "Without home advantage in 2026: Italy's 9 golds might have been lower (home advantage "
                "estimated at 3-5% performance boost). They might have won 6-7 golds instead. "
                "However, their infrastructure investments and coaching changes from 2023 would still "
                "have helped. The 2030 Games would then have given them the home advantage later."
            ),
            level="L10",
            reasoning_type="counterfactual_timing",
        ),
        TestQuestion(
            question="In a world where cross-country skiing was removed from the Olympics, "
            "how would the medal standings change?",
            expected_answer=(
                "Norway would lose 8 of 13 golds (cross-country is their strongest sport), dropping to 5 golds. "
                "Italy (9 golds, mostly alpine) would lead. Germany and US (6 each) would tie for third. "
                "The overall standings would flip dramatically - Norway's dominance depends heavily on "
                "cross-country skiing."
            ),
            level="L10",
            reasoning_type="counterfactual_structural",
        ),
    ],
)


# LEVEL 11: Novel Skill Acquisition from Documentation
# Tests learning genuinely NEW skills (gh-aw, released Jan 2026) not in training data
LEVEL_11 = TestLevel(
    level_id="L11",
    level_name="Novel Skill Acquisition",
    description=(
        "Agent must learn GitHub Agentic Workflows from documentation, apply it to "
        "solve problems, and teach it. Tests genuine learning of post-training-cutoff skills."
    ),
    articles=[
        TestArticle(
            title="GitHub Agentic Workflows: Overview and Core Concepts",
            content=(
                "GitHub Agentic Workflows (gh-aw) is a repository automation platform released "
                "in January 2026. It enables AI-powered automation within GitHub Actions using "
                "natural language markdown instructions instead of complex YAML.\n\n"
                "A workflow file lives at .github/workflows/<name>.md and has two parts:\n"
                "1. YAML frontmatter between --- markers: defines triggers, permissions, tools, "
                "engine, and safe-outputs.\n"
                "2. Markdown body: natural language instructions the AI interprets and executes.\n\n"
                "The `gh aw compile` command transforms the .md file into a .lock.yml file. "
                "Both the .md source and .lock.yml must be committed to version control. "
                "Editing markdown instructions alone does NOT require recompilation (loaded at "
                "runtime), but frontmatter changes DO require running `gh aw compile`.\n\n"
                "Three AI engines are supported: copilot (default, uses COPILOT_GITHUB_TOKEN), "
                "claude (uses ANTHROPIC_API_KEY), and codex (uses OPENAI_API_KEY). "
                "Engine is specified in frontmatter: `engine: claude`.\n\n"
                "Workflows trigger on GitHub events (issues opened, PRs created, schedules, "
                "manual dispatch, slash commands). By default, workflows have read-only permissions. "
                "All write operations go through 'safe outputs'."
            ),
            url="https://github.github.com/gh-aw/introduction/overview/",
            published="2026-01-12T10:00:00Z",
        ),
        TestArticle(
            title="GitHub Agentic Workflows: Security Architecture and Safe Outputs",
            content=(
                "gh-aw implements defense-in-depth security across three layers:\n\n"
                "1. Substrate Layer: GitHub Actions runner VMs with kernel isolation, container "
                "separation. Three privileged containers: network firewall (iptables), API proxy "
                "(holds auth tokens), MCP Gateway (spawns isolated MCP-server containers).\n\n"
                "2. Configuration Layer: YAML validation, action SHA pinning, tool allowlisting, "
                "security scanning (actionlint, zizmor, poutine).\n\n"
                "3. Plan Layer: Trusted compiler decomposes workflows into stages. SafeOutputs "
                "subsystem buffers all external writes until validation completes.\n\n"
                "SAFE OUTPUTS: The agent NEVER has direct write access. Instead:\n"
                "- Agent Job (read-only): Executes AI, buffers outputs to agent_output.json\n"
                "- Detection Job (no write): Scans for secrets/malicious patches\n"
                "- Safe Output Jobs (scoped write): Execute ONLY after detection passes\n\n"
                "Available safe output types: create-issue, add-comment, create-pull-request, "
                "add-labels, dispatch-workflow, minimize-comment.\n\n"
                "Content sanitization: @mention neutralization, bot trigger protection, "
                "XML/HTML tag conversion, URI filtering (HTTPS only), 0.5MB max content.\n\n"
                "The Agent Workflow Firewall (AWF) containerizes the agent and routes all "
                "HTTP/HTTPS through a Squid proxy with domain allowlists."
            ),
            url="https://github.github.com/gh-aw/introduction/architecture/",
            published="2026-01-12T10:00:00Z",
        ),
        TestArticle(
            title="GitHub Agentic Workflows: Tools, Patterns, and Examples",
            content=(
                "gh-aw tools configured in frontmatter: edit, bash, web-fetch, web-search, "
                "github, playwright, cache-memory, repo-memory, mcp-servers.\n\n"
                "BASH TOOL: Configurable safety. Default allows safe commands (echo, ls, cat, "
                "grep, etc). Custom whitelist: `bash: ['echo', 'git:*']`. Wildcard `:*` for "
                "unrestricted. Disabled: `bash: []`.\n\n"
                "GITHUB TOOL: Repository interaction via MCP. Toolsets: context, repos, issues, "
                "pull_requests, users, actions, code_security, search, etc. Default: context, "
                "repos, issues, pull_requests, users.\n\n"
                "MCP SERVERS: Custom tool integration. Run in isolated Docker containers. "
                "`allowed` field restricts which tools the agent can access.\n\n"
                "PATTERNS:\n"
                "- IssueOps: Triggered by issue events, automated triage/response\n"
                "- ChatOps: Slash commands (/command) in issue/PR comments\n"
                "- DailyOps: Scheduled daily workflows with fuzzy scheduling\n"
                "- MultiRepoOps: Cross-repo coordination, requires PAT\n"
                "- Orchestration: Orchestrator dispatches worker workflows, aggregates results\n"
                "- MemoryOps: Stateful via cache-memory (7-day) and repo-memory (unlimited)\n\n"
                "Compilation workflow: 1) Author .md file 2) `gh aw compile` to generate "
                ".lock.yml 3) Commit both files 4) Push to trigger or `gh aw run <name>`."
            ),
            url="https://github.github.com/gh-aw/reference/tools/",
            published="2026-01-12T10:00:00Z",
        ),
    ],
    questions=[
        TestQuestion(
            question=(
                "What is the fundamental difference between a GitHub Agentic Workflow "
                "and a traditional GitHub Actions workflow?"
            ),
            expected_answer=(
                "Agentic workflows use natural language markdown instructions interpreted "
                "by an AI engine, while traditional Actions use YAML-based conditional logic. "
                "Agentic workflows have built-in security controls (read-only defaults, safe "
                "outputs, sandboxing) and can reason about context."
            ),
            level="L11",
            reasoning_type="concept_discovery",
        ),
        TestQuestion(
            question=(
                "Write a complete gh-aw workflow file that triggers when a new issue is "
                "opened, uses Claude as the AI engine, has bash access (only git and echo), "
                "and can create comments and add labels."
            ),
            expected_answer=(
                "---\non:\n  issues:\n    types: [opened]\nengine: claude\n"
                "permissions: read-all\ntools:\n  bash: ['git:*', 'echo']\n  github:\n"
                "    toolsets: [issues, labels]\nsafe-outputs:\n  add-comment:\n  add-labels:\n"
                "---\n# Issue Label Suggester\nAnalyze the issue and suggest appropriate labels."
            ),
            level="L11",
            reasoning_type="procedural_application",
        ),
        TestQuestion(
            question=(
                "A developer wants their gh-aw workflow to directly write files during "
                "the agent execution step. Explain why this is not possible and what to use instead."
            ),
            expected_answer=(
                "The agent job runs with read-only permissions by default. Direct writes are "
                "prevented because the agent could be compromised via prompt injection. "
                "Instead, use safe outputs (like create-pull-request) which buffer output to "
                "an artifact, run a detection job to scan for malicious content, then execute "
                "the write in a separate permission-scoped job."
            ),
            level="L11",
            reasoning_type="constraint_reasoning",
        ),
        TestQuestion(
            question=(
                "Teach a junior developer how to create their first gh-aw workflow in 5 steps. "
                "Include the most common beginner mistake."
            ),
            expected_answer=(
                "1. Create .github/workflows/my-workflow.md with YAML frontmatter and markdown body. "
                "2. Run `gh aw compile` to generate .lock.yml. "
                "3. Commit both .md and .lock.yml files. "
                "4. Push to trigger, or `gh aw run my-workflow`. "
                "5. Check the Actions tab for results.\n\n"
                "Common mistake: Editing frontmatter without recompiling. Markdown body changes "
                "are loaded at runtime, but frontmatter changes require `gh aw compile`."
            ),
            level="L11",
            reasoning_type="teaching_transfer",
        ),
    ],
)


# Export all levels
ALL_LEVELS = [LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4, LEVEL_5, LEVEL_6]
TEACHER_STUDENT_LEVELS = [LEVEL_7]
ADVANCED_LEVELS = [LEVEL_8, LEVEL_9, LEVEL_10]
NOVEL_SKILL_LEVELS = [LEVEL_11]


def get_level_by_id(level_id: str) -> TestLevel | None:
    """Get a test level by its ID."""
    for level in ALL_LEVELS + TEACHER_STUDENT_LEVELS + ADVANCED_LEVELS + NOVEL_SKILL_LEVELS:
        if level.level_id == level_id:
            return level
    return None


__all__ = [
    "TestArticle",
    "TestQuestion",
    "TestLevel",
    "LEVEL_1",
    "LEVEL_2",
    "LEVEL_3",
    "LEVEL_4",
    "LEVEL_5",
    "LEVEL_6",
    "LEVEL_7",
    "LEVEL_8",
    "LEVEL_9",
    "LEVEL_10",
    "LEVEL_11",
    "ALL_LEVELS",
    "TEACHER_STUDENT_LEVELS",
    "ADVANCED_LEVELS",
    "NOVEL_SKILL_LEVELS",
    "get_level_by_id",
]
