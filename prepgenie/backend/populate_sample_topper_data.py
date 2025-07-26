#!/usr/bin/env python3
"""
Populate Vector Database with Sample Topper Data
Creates sample topper answers to test the 14-dimensional analysis system
"""

import asyncio
import logging
import sys
import os
sys.path.append('/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend')

# FORCE USE OF ZILLIZ CLOUD (using valid credentials)
os.environ['ENVIRONMENT'] = 'production'  # Force production mode to use Zilliz Cloud
os.environ['USE_ZILLIZ_CLOUD'] = 'true'
os.environ['DISABLE_VECTOR_SERVICE'] = 'false'
# Use Zilliz Cloud credentials
os.environ['MILVUS_URI'] = 'https://in03-7399fcefb79acf1.serverless.gcp-us-west1.cloud.zilliz.com'
os.environ['MILVUS_TOKEN'] = '9dd75ac2787c2074903f7fa3fae78a762482ddd693d8431c975f7ae52c154eabd11d4b6468481036f8a9940b4e1cff72313a4169'

# Also ensure the config is loaded properly
print("🔧 Environment Configuration:")
print(f"   ENVIRONMENT: {os.environ.get('ENVIRONMENT')}")
print(f"   Using ZILLIZ CLOUD: {os.environ.get('MILVUS_URI')}")
print("="*60)

from app.services.topper_vector_service import TopperVectorService

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SAMPLE_TOPPER_DATA = [
    {
        "topper_name": "Anubhav Singh",
        "institute": "VisionIAS",
        "exam_year": "2024",
        "question_text": "Discuss the role of Inter-State Council in promoting cooperative federalism in India.",
        "answer_text": """The Inter-State Council, established under Article 263 of the Constitution, serves as a crucial mechanism for promoting cooperative federalism in India.

Constitutional Framework:
Article 263 empowers the President to establish an Inter-State Council if deemed necessary in public interest. The Council consists of:
- Prime Minister as Chairman
- Chief Ministers of all states
- Union Ministers nominated by the PM
- Administrators of Union Territories

Key Functions in Cooperative Federalism:
1. Dispute Resolution: The Council provides a platform for amicable settlement of disputes between states or between Centre and states, reducing litigation.

2. Policy Coordination: It facilitates coordination of policies and their implementation across different levels of government.

3. Resource Sharing: The Council discusses resource allocation, particularly regarding subjects in the Concurrent List.

4. Administrative Cooperation: It promotes administrative cooperation between Centre and states through sharing of best practices.

Recent Initiatives:
- Regular meetings have addressed issues like GST implementation
- COVID-19 response coordination
- Digital India initiatives
- Environmental clearances

Challenges:
Despite its potential, the Council faces limitations:
- Recommendations are not binding
- Irregular meetings affect continuity
- Political differences sometimes overshadow cooperative approach

Way Forward:
To strengthen cooperative federalism, the Inter-State Council should:
- Meet more regularly with structured agenda
- Have more binding powers for dispute resolution
- Include local government representatives
- Focus on emerging challenges like climate change and urbanization

The Inter-State Council remains vital for India's federal structure, requiring continuous strengthening to address evolving governance challenges.""",
        "subject": "GS-II",
        "marks": 15,
        "question_number": "Q1"
    },
    {
        "topper_name": "Priya Sharma",
        "institute": "Drishti IAS",
        "exam_year": "2024",
        "question_text": "Analyze the effectiveness of the Directorate of Enforcement in investigating money laundering cases.",
        "answer_text": """The Directorate of Enforcement (ED) has emerged as a key investigative agency in India's fight against money laundering, operating under the Prevention of Money Laundering Act (PMLA), 2002.

Statutory Framework:
ED operates under multiple Acts:
- PMLA, 2002: Primary legislation for money laundering
- Foreign Exchange Management Act (FEMA), 1999
- Fugitive Economic Offenders Act, 2018

Investigative Powers:
1. Search and Seizure: ED can conduct searches and seize assets without prior court approval
2. Attachment of Properties: Can attach assets equivalent to money laundering proceeds
3. Arrest Powers: Can arrest accused during investigation
4. Summons Power: Can summon individuals for questioning

Effectiveness Indicators:
Positive Aspects:
- Significant increase in prosecutions (from 23 in 2014 to 888 in 2022)
- Recovery of ₹1,052 crore in 2021-22
- High-profile cases like Vijay Mallya, Nirav Modi handled effectively
- Coordination with international agencies improved

Procedural Strengths:
- Use of modern investigation techniques
- Digital forensics capabilities
- International cooperation through MLATs
- Specialized courts for faster disposal

Challenges and Criticisms:
1. Conviction Rate: Despite investigations, conviction rate remains low (around 23%)
2. Selective Targeting: Allegations of targeting political opponents
3. Prolonged Custody: Extended custody without trial raises human rights concerns
4. Resource Constraints: Limited manpower for complex financial crimes

Recent Developments:
- 2019 PMLA Amendment strengthened ED's powers
- Supreme Court judgments on arrest guidelines
- Integration with financial intelligence units

Recommendations:
- Improve prosecution quality for higher conviction rates
- Ensure transparency in case selection
- Strengthen specialized courts
- Enhanced training for officers
- Better coordination with other agencies

While ED has shown improved performance in recent years, balanced approach ensuring both effectiveness and due process is essential for maintaining public trust.""",
        "subject": "GS-II",
        "marks": 15,
        "question_number": "Q2"
    },
    {
        "topper_name": "Rakesh Kumar",
        "institute": "Chandigarh Academy",
        "exam_year": "2024",
        "question_text": "Evaluate the success of the Indian Constitution in providing a framework for liberal democracy.",
        "answer_text": """The Indian Constitution has been remarkably successful in providing a robust framework for liberal democracy, enabling India to maintain democratic governance for over seven decades despite numerous challenges.

Liberal Democracy Framework:
The Constitution incorporates key elements of liberal democracy:
- Popular sovereignty through adult suffrage
- Separation of powers with checks and balances
- Independent judiciary
- Fundamental rights protection
- Rule of law
- Pluralistic political system

Key Successes:

1. Electoral Democracy:
- Regular, free, and fair elections at all levels
- Peaceful transfer of power between different parties
- Universal adult suffrage from inception
- Independent Election Commission ensuring electoral integrity

2. Rights Protection:
- Fundamental Rights as justiciable rights
- Supreme Court as guardian of rights
- Public Interest Litigation for rights enforcement
- Protection of minorities and vulnerable sections

3. Federal Structure:
- Balance between unity and diversity
- Successful accommodation of linguistic and cultural diversity
- Cooperative federalism through institutions like Finance Commission

4. Judicial Independence:
- Supreme Court and High Courts maintaining independence
- Judicial review as check on legislative and executive power
- Evolution of basic structure doctrine

5. Political Pluralism:
- Multi-party system with regular alternation of power
- Coalition governments reflecting diverse opinions
- Space for dissent and opposition

Challenges Addressed:

1. Emergency Period (1975-77):
Initially seen as failure, but the Constitution's resilience was demonstrated when:
- Democratic institutions were restored
- 42nd and 44th Amendments strengthened democracy
- Basic Structure Doctrine prevented constitutional destruction

2. Diversity Management:
- Successful integration of princely states
- Linguistic reorganization of states
- Protection of minority rights
- Reservation policies for social justice

3. Institutional Evolution:
- Independent constitutional bodies (CAG, CEC, etc.)
- Right to Information Act strengthening transparency
- Lokpal and Lokayukta for anti-corruption

Contemporary Relevance:

Recent Positive Developments:
- Digital democracy initiatives
- Increased voter participation
- Youth engagement in democratic processes
- Transparency through technology

Ongoing Challenges:
- Polarization affecting democratic discourse
- Media freedom concerns
- Electoral funding transparency
- Judicial delays

Global Comparison:
India's democracy has shown remarkable resilience compared to many post-colonial nations, maintaining:
- Constitutional continuity without military coups
- Democratic legitimacy through regular elections
- Protection of diversity in unity

Conclusion:
The Indian Constitution has largely succeeded in providing a framework for liberal democracy. While challenges exist, the self-correcting mechanisms within the Constitution, combined with active civil society and independent institutions, continue to strengthen Indian democracy. The Constitution's flexibility has allowed adaptation to changing needs while maintaining core democratic values.

The success is evident in India being recognized as the world's largest democracy, with democratic institutions remaining vibrant despite occasional stress.""",
        "subject": "GS-II",
        "marks": 15,
        "question_number": "Q3"
    },
    {
        "topper_name": "Sanskriti Trivedy",
        "institute": "VisionIAS", 
        "exam_year": "2024",
        "question_text": "Discuss the challenges and opportunities in India's transition to renewable energy.",
        "answer_text": """India's transition to renewable energy represents both a critical necessity and a tremendous opportunity in addressing climate change while ensuring energy security.

Current Renewable Energy Landscape:
- Installed capacity: 175 GW (as of 2023)
- Target: 500 GW by 2030
- Share in total capacity: ~40%
- Key sources: Solar (70 GW), Wind (65 GW), Hydro, Biomass

Key Opportunities:

1. Climate Leadership:
- Paris Agreement commitments (reduce emission intensity by 45% by 2030)
- Net-zero pledge by 2070
- International climate finance access
- Green hydrogen mission potential

2. Economic Benefits:
- Job creation (estimated 3.4 million jobs by 2030)
- Reduced import dependency (₹12 lakh crore savings on oil imports)
- Export opportunities in green technologies
- Attracting green investments

3. Technological Advantages:
- Declining costs of solar and wind power
- Grid parity achieved in many regions
- Storage technology improvements
- Digital grid management capabilities

4. Manufacturing Potential:
- PLI schemes for solar PV manufacturing
- Wind turbine manufacturing ecosystem
- Battery manufacturing initiatives
- Green hydrogen production

Major Challenges:

1. Infrastructure Constraints:
- Grid integration issues with intermittent sources
- Transmission line constraints
- Storage infrastructure deficit
- Rural grid connectivity gaps

2. Financial Challenges:
- High upfront capital costs
- State electricity board financial stress
- Land acquisition costs
- Payment delays to renewable developers

3. Technical Challenges:
- Grid stability with variable renewable energy
- Energy storage technology costs
- Skill gap in renewable energy sector
- Technology dependence on imports

4. Policy and Regulatory Issues:
- Inconsistent state policies
- Land acquisition challenges
- Environmental clearance delays
- Tariff and subsidy rationalization

5. Social and Environmental Concerns:
- Land use conflicts with farmers
- Impact on wildlife (wind turbines)
- Water usage in solar panel cleaning
- Disposal of solar panels/wind turbines

Government Initiatives:

Policy Framework:
- National Solar Mission (100 GW solar by 2022)
- PM-KUSUM for agricultural solar pumps
- Green Energy Corridor for transmission
- RPO (Renewable Purchase Obligation) mandates

Financial Support:
- Viability Gap Funding schemes
- Solar park development
- Rooftop solar subsidies
- Green bonds and climate finance

International Cooperation:
- International Solar Alliance leadership
- Clean energy partnerships with countries
- Technology transfer agreements
- Climate finance mobilization

Way Forward:

1. Grid Modernization:
- Smart grid development
- Flexible grid operations
- Advanced forecasting systems
- Regional grid integration

2. Storage Solutions:
- Battery energy storage systems
- Pumped hydro storage
- Green hydrogen for storage
- Demand response programs

3. Manufacturing Ecosystem:
- Domestic manufacturing incentives
- R&D in renewable technologies
- Skill development programs
- Innovation hubs

4. Just Transition:
- Reskilling coal sector workers
- Alternative livelihoods in coal regions
- Community participation in renewable projects
- Environmental rehabilitation

5. Financial Innovation:
- Green bonds market development
- Blended finance mechanisms
- Carbon markets participation
- International climate finance access

Conclusion:
India's renewable energy transition, while challenging, presents unprecedented opportunities for sustainable development. Success requires coordinated efforts across policy, technology, finance, and social dimensions. The transition is not just an environmental imperative but an economic opportunity that can position India as a global leader in clean energy.""",
        "subject": "GS-III",
        "marks": 15,
        "question_number": "Q4"
    },
    {
        "topper_name": "Arjun Patel",
        "institute": "Forum IAS",
        "exam_year": "2024", 
        "question_text": "Analyze the role of civil services in governance and democratic accountability in India.",
        "answer_text": """Civil services form the permanent executive in India's governance system, playing a crucial role in policy implementation and ensuring continuity in administration while maintaining democratic accountability.

Constitutional Framework:
- Articles 309-323 provide constitutional basis for civil services
- All India Services (IAS, IPS, IFS) and Central Services
- Part XIV ensures security of tenure and conditions of service
- Article 311 provides protection against arbitrary dismissal

Role in Governance:

1. Policy Implementation:
- Translation of political decisions into administrative action
- Ensuring uniform implementation across the country
- Providing continuity during political transitions
- Bridging gap between policy formulation and ground reality

2. Advisory Functions:
- Providing technical expertise to political executive
- Policy analysis and option assessment
- Inter-ministerial coordination
- International negotiations and representations

3. Service Delivery:
- Direct interface with citizens
- Implementation of welfare schemes
- Regulatory functions
- Crisis management and disaster response

4. Institutional Memory:
- Maintaining administrative continuity
- Preserving institutional knowledge
- Learning from past experiences
- Facilitating smooth transitions

Democratic Accountability Mechanisms:

1. Constitutional Accountability:
- Oath of office and allegiance to Constitution
- Fundamental duties as citizens
- Protection of fundamental rights
- Secular and impartial service

2. Political Accountability:
- Accountability to elected representatives
- Parliamentary questions and debates
- Legislative oversight through committees
- Minister's responsibility for administrative actions

3. Legal Accountability:
- Judicial review of administrative actions
- Central Administrative Tribunal (CAT) jurisdiction
- Right to Information Act transparency
- Anti-corruption agencies oversight

4. Social Accountability:
- Citizen's Charter commitments
- Grievance redressal mechanisms
- Public participation in governance
- Civil society monitoring

Challenges to Accountability:

1. Political Interference:
- Pressure for partisan decisions
- Frequent transfers affecting continuity
- Misuse of discretionary powers
- Conflict between political and administrative priorities

2. Structural Issues:
- Complex hierarchical system
- Overlapping jurisdictions
- Bureaucratic delays
- Risk-averse culture

3. Capacity Constraints:
- Skill gaps in emerging areas
- Technology adaptation challenges
- Training and development needs
- Performance evaluation systems

4. Ethical Concerns:
- Corruption and rent-seeking
- Nepotism and favoritism
- Lack of transparency
- Conflict of interest situations

Reforms for Enhanced Accountability:

1. Administrative Reforms:
- Performance-based evaluation systems
- Lateral entry for specialized skills
- Training and capacity building
- Technology integration

2. Transparency Measures:
- Strengthening RTI implementation
- Online service delivery
- Social audits
- Citizen feedback mechanisms

3. Institutional Reforms:
- Civil Services Board for transfers/postings
- Fixed tenure in sensitive positions
- Specialization in service cadres
- Professional development programs

4. Legal and Regulatory Reforms:
- Whistleblower protection
- Fast-track corruption cases
- Asset declaration systems
- Conflict of interest guidelines

Best Practices:

1. Mission Mode Approach:
- JAM (Jan Dhan-Aadhaar-Mobile) trinity
- Digital India initiatives
- Direct benefit transfer schemes
- E-governance platforms

2. Innovation in Service Delivery:
- Single window clearances
- Time-bound services
- Mobile governance
- Artificial intelligence applications

3. Collaborative Governance:
- Public-private partnerships
- Civil society engagement
- Citizen participation
- Inter-governmental cooperation

Contemporary Relevance:

Recent Developments:
- Mission Karmayogi for capacity building
- PM-GATI SHAKTI for infrastructure coordination
- Ease of doing business initiatives
- COVID-19 response coordination

Future Challenges:
- Digital transformation requirements
- Climate change adaptation
- Demographic dividend utilization
- Sustainable development goals

Conclusion:
Civil services remain central to India's governance framework, with their effectiveness directly impacting democratic outcomes. While challenges exist, ongoing reforms focus on enhancing accountability, transparency, and performance. The key lies in balancing administrative autonomy with democratic oversight, ensuring that civil services serve the Constitution and people while remaining responsive to elected representatives.

Success in governance requires civil services that are competent, ethical, and accountable while maintaining political neutrality and professional integrity.""",
        "subject": "GS-II",
        "marks": 15,
        "question_number": "Q5"
    }
]

async def populate_topper_database():
    """Populate the vector database with sample topper data"""
    
    print("🚀 POPULATING VECTOR DATABASE WITH SAMPLE TOPPER DATA")
    print("=" * 60)
    
    # Initialize vector service
    vector_service = TopperVectorService()
    
    try:
        # Connect to vector service
        print("📡 Connecting to vector service...")
        await vector_service.connect()
        await vector_service.initialize()
        print("✅ Vector service connected and initialized")
        
        # Insert sample topper data
        print(f"\n📚 Inserting {len(SAMPLE_TOPPER_DATA)} sample topper answers...")
        
        for i, topper_data in enumerate(SAMPLE_TOPPER_DATA, 1):
            try:
                print(f"   {i}. Adding {topper_data['topper_name']} - {topper_data['question_text'][:50]}...")
                
                # Store topper content
                result = await vector_service.store_topper_content(
                    topper_name=topper_data['topper_name'],
                    institute=topper_data['institute'],
                    exam_year=topper_data['exam_year'],
                    question_text=topper_data['question_text'],
                    answer_text=topper_data['answer_text'],
                    subject=topper_data['subject'],
                    marks=topper_data['marks'],
                    question_number=topper_data['question_number'],
                    metadata={'source_file': 'sample_data'}
                )
                
                print(f"      ✅ Successfully stored (ID: {result})")
                
            except Exception as e:
                print(f"      ❌ Failed to store: {e}")
                continue
        
        # Test the populated database
        print("\n🔍 TESTING POPULATED DATABASE:")
        
        # Check entity count
        entity_count = vector_service._topper_collection.num_entities
        print(f"   📊 Total entities in database: {entity_count}")
        
        # Test search with sample query
        test_query = "Discuss the role of Inter-State Council in promoting cooperative federalism"
        print(f"   🔍 Testing search with query: {test_query[:50]}...")
        
        results = await vector_service.search_similar_topper_answers(
            query_question=test_query,
            limit=3
        )
        
        print(f"   📈 Search returned {len(results)} results:")
        for j, result in enumerate(results, 1):
            similarity = result.get('similarity_score', 0)
            topper_name = result.get('topper_name', 'Unknown')
            print(f"      {j}. {topper_name} (similarity: {similarity:.3f})")
        
        print("\n🎉 DATABASE POPULATION COMPLETE!")
        print("✅ Your system should now provide 14-dimensional analysis with topper comparison")
        print("🔄 Try uploading a PDF again to test the enhanced analysis")
        
    except Exception as e:
        print(f"❌ Error populating database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(populate_topper_database())
