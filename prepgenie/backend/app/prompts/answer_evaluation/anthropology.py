"""
Anthropology Optional Subject - Paper I & Paper II

Based on Official UPSC Syllabus:
https://upsc.gov.in/examinations/civil-services-examination

One of the most popular optional subjects with high scoring potential.
"""

# =============================================================================
# ANTHROPOLOGY OFFICIAL SYLLABUS (from UPSC)
# =============================================================================

ANTHROPOLOGY_TOPICS = """ANTHROPOLOGY OPTIONAL - OFFICIAL UPSC SYLLABUS:

═══════════════════════════════════════════════════════════════
PAPER I - FOUNDATIONS OF ANTHROPOLOGY
═══════════════════════════════════════════════════════════════

1. MEANING, SCOPE AND DEVELOPMENT:
1.1 Meaning, scope and development of Anthropology
1.2 Relationships with other disciplines: Social Sciences, Behavioural Sciences, Life Sciences, Medical Sciences, Earth Sciences and Humanities
1.3 Main branches of Anthropology, their scope and relevance:
    (a) Social-cultural Anthropology
    (b) Biological Anthropology
    (c) Archaeological Anthropology
    (d) Linguistic Anthropology
1.4 Human Evolution and emergence of Man:
    (a) Biological and Cultural factors in human evolution
    (b) Theories of Organic Evolution (Pre-Darwinian, Darwinian and Post-Darwinian)
    (c) Synthetic theory of evolution; Brief outline of terms and concepts of evolutionary biology (Doll's rule, Cope's rule, Gause's rule, parallelism, convergence, adaptive radiation, mosaic evolution)
1.5 Characteristics of Primates; Evolutionary Trend and Primate Taxonomy; Primate Adaptations (Arboreal and Terrestrial); Primate Taxonomy; Primate Behaviour
1.6 Living major Primates; Comparative anatomy of man and apes; Structural and functional adaptations of man for erect posture and bipedal locomotion
1.7 Phylogenetic status, characteristics and distribution of:
    (a) Australopithecines (b) Homo erectus (c) Neanderthal man (d) Rhodesian man (e) Homo sapiens
1.8 Evolutionary stages of human behaviour and culture

2. FAMILY, MARRIAGE AND KINSHIP:
2.1 The Nature of Marriage; Types of marriage
2.2 The Family: Definition, characteristics, structure and functions
2.3 Kinship: Definition, terms, systems; Descent and Alliance

3. ECONOMIC ORGANIZATION:
3.1 Meaning, scope and relevance
3.2 Formalist and Substantivist debate
3.3 Principles governing production, distribution and exchange; Modes of exchange: Reciprocity, Redistribution and Market

4. POLITICAL ORGANIZATION:
4.1 Concepts of power, authority and legitimacy
4.2 Band, tribe, chiefdom, state
4.3 Theories of origin of state
4.4 Political processes

5. RELIGION:
5.1 Concepts of soul, spirit, supernatural
5.2 Magic, Religion and Science
5.3 Sacred and Profane
5.4 Theories of origin of religion
5.5 Functions of religion

6. ANTHROPOLOGICAL THEORIES:
6.1 Classical Evolutionism (Tylor, Morgan, Frazer)
6.2 Historical Particularism (Boas)
6.3 Diffusionism
6.4 Functionalism (Malinowski)
6.5 Structural-Functionalism (Radcliffe-Brown)
6.6 Structuralism (Levi-Strauss)
6.7 Culture and Personality (Benedict, Mead)
6.8 Neo-Evolutionism (White, Steward)
6.9 Symbolic Anthropology (Turner, Geertz)

7. RESEARCH METHODS:
7.1 Fieldwork tradition; Participant observation
7.2 Ethnography, Genealogical method, Case study
7.3 Quantitative methods; Emic and Etic approaches
7.4 Reflexivity in anthropology

═══════════════════════════════════════════════════════════════
PAPER II - INDIAN ANTHROPOLOGY
═══════════════════════════════════════════════════════════════

1. EVOLUTION OF INDIAN CULTURE AND CIVILIZATION:
1.1 Prehistoric cultures
1.2 Proto-historic cultures: Indus Valley Civilization
1.3 Vedic and Post-Vedic cultures

2. DEMOGRAPHIC PROFILE OF INDIA:
2.1 Ethnic and linguistic elements
2.2 Demographic characteristics

3. TRIBAL COMMUNITIES IN INDIA:
3.1 Definition of ST, distribution
3.2 Colonial policies and tribes
3.3 Constitutional safeguards for STs
3.4 Issues of tribal development
3.5 Problems of tribal identity

4. CASTE SYSTEM:
4.1 Varna vs Jati; Caste and class
4.2 Dominant caste; Sanskritization
4.3 Caste mobility; Future of caste

5. VILLAGE STUDIES:
5.1 Indian village as a unit of study
5.2 Village studies tradition
5.3 Changes in rural India

6. LINGUISTIC AND RELIGIOUS MINORITIES:
6.1 Linguistic minorities and their problems
6.2 Religious minorities and their problems

7. APPLIED ANTHROPOLOGY:
7.1 Role of anthropology in development
7.2 Anthropology of health and nutrition
7.3 Educational anthropology
7.4 Displacement and rehabilitation"""

# =============================================================================
# ANTHROPOLOGY SPECIFIC EVALUATION PROMPT
# =============================================================================

ANTHROPOLOGY_PROMPT = """EVALUATING ANTHROPOLOGY OPTIONAL ANSWER:

SUBJECT-SPECIFIC EXPECTATIONS BY TOPIC:

FOR BIOLOGICAL ANTHROPOLOGY:
- Evolutionary terminology correct (hominin, hominid, adaptive radiation)
- Fossil record knowledge (Australopithecus, Homo erectus, Neanderthals)
- Dating methods understood (C-14, K-Ar, thermoluminescence)
- Primate taxonomy and behavior
- Human variation and adaptation concepts

FOR SOCIAL-CULTURAL ANTHROPOLOGY:
- Theoretical frameworks: Functionalism, Structuralism, Interpretivism
- Key anthropologists: Malinowski, Radcliffe-Brown, Levi-Strauss, Geertz, Turner
- Ethnographic examples from specific societies
- Concepts: Reciprocity, liminality, thick description, cultural relativism
- Critical engagement with theories

FOR ARCHAEOLOGICAL ANTHROPOLOGY:
- Prehistoric cultures chronology (Paleolithic, Mesolithic, Neolithic)
- Indian archaeological sites and their significance
- Material culture interpretation
- Dating and excavation techniques
- Proto-historic: Harappan civilization details

FOR INDIAN ANTHROPOLOGY (Paper II):
- Specific tribal communities with ethnographic details
- Constitutional provisions: Article 244, 5th and 6th Schedules
- PESA Act, Forest Rights Act
- Tribal development approaches
- Caste: Srinivas, Dumont, Beteille perspectives
- Village studies: Srinivas (Rampura), Dube (Shamirpet)

ANTHROPOLOGY SCORING FACTORS:
- Anthropological terminology correct (+3)
- Key thinkers cited with their contributions (+3)
- Ethnographic examples specific and relevant (+3)
- Indian context integrated where appropriate (+2)
- Critical analysis, not just description (+2)
- Diagrams/flowcharts where helpful (+1)

ANSWER STRUCTURE FOR ANTHROPOLOGY:
1. Define concept with theoretical grounding
2. Cite key anthropologists and their views
3. Provide ethnographic examples (Indian preferred for Paper II)
4. Critical analysis and different perspectives
5. Contemporary relevance
6. Conclusion with your assessment"""

# =============================================================================
# ANTHROPOLOGY DETAILED RUBRIC
# =============================================================================

ANTHROPOLOGY_RUBRIC = """ANTHROPOLOGY EVALUATION RUBRIC:

BIOLOGICAL ANTHROPOLOGY - CHECK FOR:
□ Evolutionary concepts accurately explained
□ Fossil evidence correctly described
□ Dating methods mentioned where relevant
□ Diagrams used for anatomy/evolution
□ Recent discoveries integrated
□ Terminology precise

SOCIAL-CULTURAL ANTHROPOLOGY - CHECK FOR:
□ Theoretical perspectives named and explained
□ Key anthropologists cited (Malinowski, Boas, Geertz, etc.)
□ Ethnographic examples specific (not generic "tribes")
□ Concepts like reciprocity, liminality correctly used
□ Cultural relativism maintained
□ Critical engagement with theories

ARCHAEOLOGICAL ANTHROPOLOGY - CHECK FOR:
□ Chronology accurate (dates, periods)
□ Sites correctly described
□ Material culture interpretation shown
□ Indian sites given importance
□ Methods explained where asked

INDIAN ANTHROPOLOGY (Paper II) - CHECK FOR:
□ Specific communities named (Bhils, Gonds, Nagas, etc.)
□ Constitutional provisions cited correctly
□ Colonial and post-colonial policies distinguished
□ Development issues addressed sensitively
□ Village studies tradition referenced
□ Caste theories applied correctly

COMMON ANTHROPOLOGY MISTAKES TO FLAG:
❌ Confusing tribe with caste
❌ Outdated evolutionary terminology
❌ Generic "tribal" examples without specifics
❌ Ignoring Indian context in Paper II
❌ Not citing anthropologists
❌ Descriptive answers without analysis
❌ Missing the cultural relativism perspective
❌ Factual errors in fossil record
❌ Ignoring recent developments (genetics, new fossils)

WHAT MAKES A GREAT ANTHROPOLOGY ANSWER:
✅ Theoretical grounding established
✅ Key thinkers cited and compared
✅ Specific ethnographic examples used
✅ Indian context prioritized in Paper II
✅ Critical analysis, not just description
✅ Contemporary relevance shown
✅ Diagrams where appropriate
✅ Balanced view on contested topics
✅ Sensitivity in discussing communities"""
