| Grounding         | LLM | Reasoning |                                    | with Knowledge     | Graphs |
| ----------------- | --- | --------- | ---------------------------------- | ------------------ | ------ |
| AlfonsoAmayuelas∗ |     |           | JoySain,SimerjotKaur,ChareseSmiley |                    |        |
| UCSantaBarbara    |     |           |                                    | JPMorganAIResearch |        |
amayuelas@ucsb.edu joy.sain, simerjot.kaur, charese.h.smiley@jpmchase.com
Abstract
5202 ceD 4  ]LC.sc[  3v74231.2052:viXra
LargeLanguageModels(LLMs)excelatgeneratingnaturallanguageanswers,yet
| theiroutputsoftenremainunverifiableanddifficulttotrace. |     |     |     | KnowledgeGraphs |     |
| ------------------------------------------------------- | --- | --- | --- | --------------- | --- |
(KGs)offeracomplementarystrengthbyrepresentingentitiesandtheirrelation-
shipsinstructuredform,providingafoundationformorereliablereasoning. We
| propose                                                 | a novel | framework | that integrates | LLM reasoning with | KGs by link-  |
| ------------------------------------------------------- | ------- | --------- | --------------- | ------------------ | ------------- |
| ingeachstepofthereasoningprocesstograph-structureddata. |         |           |                 |                    | Thisgrounding |
turnsintermediate“thoughts”intointerpretabletracesthatremainconsistentwith
| external | knowledge. | Our approach | incorporates | multiple reasoning | strategies, |
| -------- | ---------- | ------------ | ------------ | ------------------ | ----------- |
Chain-of-Thought(CoT),Tree-of-Thought(ToT),andGraph-of-Thought(GoT),
| and is evaluated                  |             | on GRBench, | a benchmark      | for domain-specific             | graph reason- |
| --------------------------------- | ----------- | ----------- | ---------------- | ------------------------------- | ------------- |
| ing. Our                          | experiments | show        | state-of-the-art | (SOTA) performance,             | with at least |
| 26.5%improvementoverCoTbaselines. |             |             |                  | Beyondaccuracy,weanalyzehowstep |               |
depth,branchingstructure,andmodelsizeinfluencereasoningquality,offering
| insightsintotheconditionsthatsupporteffectivereasoning. |     |     |     | Together,thesecon- |     |
| ------------------------------------------------------- | --- | --- | --- | ------------------ | --- |
tributionshighlighthowgroundingLLMsinstructuredknowledgeenablesboth
higheraccuracyandgreaterinterpretabilityincomplexreasoningtasks.
1 Introduction
LLMshaveshownremarkableversatilityinansweringquestionsposedinnaturallanguage. This
ismainlyduetotheirabilitytogeneratetext,theirbroadinternalknowledge,andtheircapacityto
accessexternalinformation[Zhuangetal.,2023,Lewisetal.,2020]. However,asignificantarea
forimprovementistheirtendencytoproduceinformationthat,whileplausible-sounding,isoften
unverifiableandlackstraceableoriginsandsources[Tonmoyetal.,2024]. Thislimitationhighlights
adeeperissueinhowLLMsorganizeandapplyreasoning,especiallywhenreliableandaccountable
outputsarerequired.
TheLLMgenerationprocessheavilyreliesontheirinternalparameters,makingitdifficulttolink
theiroutputstoexternalsources[Koetal.,2024,Zhengetal.,2024]. Thislimitationchallengestheir
reliabilityinindustrialapplications[LuoandSpecia,2024]. Inappliedsettings,whereLLMshandle
criticaloperations,integratingthemwithdomain-specificknowledgeisessential. Fine-tuningLLMs
fornewdomainsislabor-intensive,especiallyforcompanieswithproprietarydatafacingprivacy
andlegalissues. Asaresult,thereisaneedforinterventionsthatguidereasoningprocessessothat
outputsremainaccurateandtransparentwithoutrequiringexhaustivere-training.
Methods such as Retrieval-Augmented Generation (RAG) [Lewis et al., 2020] and SQL-based
querying[Rajkumaretal.,2022]addressthisgappartially. However,theyoftenfailtocapturethe
dynamicrelationshipsbetweenconceptsthatarenecessaryforcomprehensiveunderstanding. These
approachestypicallyassumethatknowledgeiswell-representedindiscreteunits,suchasdocuments
ortables,whichcanleadtoincompleteinsightswhendealingwithinterconnectedknowledgethat
spansmultiplesources. Thislimitstheabilitytosupportreasoningovercomplexqueries.
∗WorkcompletedduringaninternshipatJPMorganAIResearch
39th Conference on Neural Information Processing Systems (NeurIPS 2025) Workshop: Foundations of
ReasoninginLanguageModels.

Figure 1: Methods for Question-Answering in KGs (Section 4). Left: Agent. LLM decides to
takeoneofthepredefinedactionstoconnectwiththegraph. Right: AutomaticGraphExploration.
Entitiesareextractedineachreasoningstep,triggeringasearchforeachidentifiedentity.
KGscapturesuchrelationshipsbyorganizingentitiesandtheirconnectionsinastructuredrepre-
sentation. RecentworkhasbeguntoexplorehowKGscanguidereasoninginLLMs[Luoetal.,
2024]. Buildingonthisdirection,weproposeaframeworkthatintegratesreasoningstrategieswith
domain-specificKGsfromtheGRBenchdataset. Eachreasoningstepisexplicitlyconnectedtothe
graph,producinganswersthatarebothaccurateandtraceable. Weevaluatethreestrategies,CoT,ToT,
andGoT,whichprovidedifferentwaysoforganizingreasoningtraces(Figure2). Ourframework
achievesSOTAperformanceonGRBench,improvingbyatleast26.5%overCoTbaselines. Beyond
accuracy, we analyze how reasoning behaviors vary with step depth, branching, and model size
(Section7),offeringinsightsintohowreasoningevolvesduringinferenceandhowitcanbeshaped
bystructuredknowledge. Ourcontributionscanbesummarizedasfollows:
• Wepresentaversatileframeworkthatlinksreasoningstepswithgraphsearch,providingan
interventionthatcanbeappliedacrossdomainsandknowledgesettings.
• Weshowsubstantialgainsoverexistingreasoningstrategies,withstate-of-the-artperfor-
manceonGRBenchandanimprovementofatleast26.5%comparedtoCoTbaselines.
• Weconductadetailedstudyofhowreasoningqualityisinfluencedbystepdepth,branch-
ingstructure,andmodelsize,offeringinsightsintotheconditionsunderwhichdifferent
interventionssucceed(Section7).
• Bysystematicallygroundingeachstepinaknowledgegraph,weimproveboththeaccuracy
andthetraceabilityofoutputs,creatingreasoningtracesthatareinterpretableandverifiable.
2 RelatedWork
LLMsrequiresubstantialdataandresourcesfortrainingVillalobosetal.[2022].Retrieval-Augmented
Generation(RAG)enablethemodelstoincorporateexternalevidenceatinferencetime[Lewisetal.,
2020,Khattabetal.,2022]. RecentworkfurthercombinesRAGwithstructuredknowledge,suchas
ontologiesandKGs,toimprovefactualityandreasoningLietal.[2024],underscoringthegrowing
importanceofstructureddataforrobustanddomain-adaptableLLMs.
StructuredKnowledge Structuredknowledge,suchasdatabasesorKGs,providesorganizations
withreliablesourcesofinformationthatcanbesystematicallymaintainedandautomaticallyupdated.
KGsinparticularofferanadaptableknowledgemodelthatcapturescomplexrelationshipsbetween
interconnected concepts. Research has explored models that can interact with multiple types of
structured knowledge, such as StructLM [Zhuang et al., 2024], and approaches that incorporate
structuredknowledgeduringpretrainingtoimprovemodelperformance[Moiseevetal.,2022].
2

IntegratingKGswithLLMs TheintegrationofKGswithLLMshasemergedasapromising
direction to strengthen reasoning capabilities and reliability [Peng et al., 2024]. In general, four
primarymethodscanbedistinguished: (1)learninggraphrepresentations[Fatemietal.,2024,Chai
etal.,2023],thoughlatentrepresentationsoftenunderperformcomparedtotext-basedmethodson
KnowledgeGraphQuestionAnswering(KGQA)tasks; (2)usingGraphNeuralNetwork(GNN)
retrieverstoextractrelevantentitiesandfeedingthemastext-basedinputtothemodel[Heetal.,
2024,MavromatisandKarypis,2024];(3)generatingcode,suchasSPARQLqueries,todirectly
retrieveinformationfromgraphs[Lietal.,2023];and(4)step-by-stepinteractionmethodsthatallow
iterativereasoningovergraphs[Luoetal.,2024,Yuetal.,2022,Luoetal.,2023],whichcurrently
achievethestrongestresultsonKGQAbenchmarks.
LLMReasoningwithGraphs Beyondretrieval,KGshavealsobeenstudiedasameanstostructure
andanalyzethereasoningprocessesofLLMsthemselvesWangetal.[2024]. Thisintegrationenables
morecoherentandcontextuallyrelevantoutputswhilealsosupportingthetracingandverificationof
reasoningsteps. Themosteffectivemethodstypicallyrelyoninteractive,step-by-stepengagement
betweenLLMsandgraphs,asdiscussedabove. Examplesofthisapproachincludesystemssuch
asSunetal.[2024],Wenetal.[2024],Luoetal.[2024],Kimetal.[2023],Lietal.[2025],which
demonstrateimprovedreasoningperformancethroughgraph-basedscaffolding.Morerecentworkhas
furtherinvestigatedtheintegrationoftraditionalreasoningstrategies,suchasCoTandtree-structured
reasoning,intoKG-basedinteraction[Jinetal.,2024,Markowitzetal.,2024].
Buildingontheseadvances,ourframeworkintegratesestablishedreasoningstrategiesdirectlywith
domain-specificKGs. UnlikepreviousmethodsthattreatKGsasretrievaltoolsorrelyonlatent
representations,ourapproachsystematicallylinkseachreasoningsteptographentitiesandrelations.
3 Background
Inthissection,weformalizetheprerequisiteknowledgerelevanttothispaper. Weusep todenote
θ
apre-trainedlanguagemodelwithparametersθ,andlettersx,y,ztorefertoalanguagesequence.
x=(x ,x ,...,x ),whereeachgeneratedtokenisx isasuchthatp (x)=
(cid:81)n
p (x |x ).
1 2 n i θ i=1 θ i 1...i−1
KnowledgeGraphs(KGs) AKGisaheterogeneousdirectedgraphthatcontainsfactualknowledge
tomodelstructuredinformation. Nodesrepresententities,events,orconcepts,whileedgesrepresent
theconnectionandtypesofrelationsbetweenthem. Formally,aKGisrepresentedasG,definedbya
setoftriplesG = {(h,r,t) | h,t ∈ E,r ∈ R},whereE,Rdenotethesetofentitiesandrelations,
respectively. KGsprovideastructuredframeworkthatcanguidereasoningprocessesbyexplicitly
representingtherelationshipsbetweenconcepts.
KnowledgeGraphQuestion-Answering(KGQA) ItisareasoningtaskthatleveragesKGs. Given
anaturallanguagequestion,q,andanassociatedKG,G,thegoalistodevelopamethodthatretrieves
thecorrectanswer,a,basedontheknowledgeextractedfromtheKG:a=f(q,G).Beyondretrieving
facts,KGQAoftenrequiresintegratingmultiplereasoningstepsthattraversethegraphtoconnect
relatedconcepts.
Step-by-stepReasoningwithLLMs ToimprovethereasoningcapabilitiesofLLMsatinference
time,acommonapproachistogenerateintermediatereasoningsteps. Thekeyideaistheintroduction
ofintermediatesteps,Z =z ,...,z ,toaddinferencesourcestobridgetheqanda. Thisdecompo-
pθ 1 n
sitionallowsmodelstotacklecomplex,multi-stepproblemsincrementally,focusingcomputational
effortonpartsofreasoningchainthatrequiredeeperanalysis. StepwisereasoningoverKGsoffersa
naturalmechanismtotrack,guide,andinterpretthereasoningprocess.
4 Method
ThisworkdemonstrateshowprogressivelyconditioningLLMreasoningateachstepcanenhance
performanceondomain-specificquestionansweringoverknowledgegraphs.Bystructuringreasoning
intoincrementalstepsthatinteractwithgraphdata,themodelcanmanagecomplexdependenciesand
dynamicallyrefineitsconclusions. OurmethodcombinesreasoningstrategiesforLLMs: CoT,ToT,
GoT with2graphinteractionmethods: (1)Agent,anagenttonavigatethegraph;and(2)Automatic
GraphExploration,anautomaticgraphtraversalmechanismbasedonthegeneratedtext.
3

| (a)Chainof   | (b)TreeofThought |     | (c)GraphofThought |       |     |
| ------------ | ---------------- | --- | ----------------- | ----- | --- |
| Thought(CoT) | (ToT)            |     |                   | (GoT) |     |
Figure2: ReasoningStrategies: ThisfigureillustratesdifferentLLMreasoningstrategiestonavigate
thepotentialanswerspace: CoT,ToT,GoT.Eachstrategyconsistsof"thoughts"connectedtotheKG
throughsearchmethods(Section4.2)illustratingstepwisereasoningoverstructuredknowledge.
4.1 ReasoningStrategies
Chain-of-Thought (CoT) CoT is a well-known reasoning method that involves generating a
sequence of logical steps, where each step builds upon previous ones, ultimately leading to a
conclusion. Formally,itgeneratesasequenceofreasoningstepsZ (q)={z ,z ,...,z },where
|     |     |     | pθ  | 1 2 n |     |
| --- | --- | --- | --- | ----- | --- |
eachstepz issampledsequentiallygiventheinputqueryq,allpreviousstepsandgraphinformation
i
| fromallsteps,G′,asz | ∼pCoT(z |q,G′,z |                                              |     |     |     |
| ------------------- | --------------- | -------------------------------------------- | --- | --- | --- |
|                     | i i 1...i−1     | ). Thefinalansweraisderivedfromthisreasoning |     |     |     |
θ
process given all the generated thoughts a ∼ pCoT(a|q,G′,z ). In practice, it is sampled as a
|     |     | θ   | 1...n |     |     |
| --- | --- | --- | ----- | --- | --- |
continuouslanguagesequence. Figure2arepresentsthismethod,whereeachstepislinkedtotheKG.
Tree-of-Thought(ToT) ToTgeneralizesCoTbymodelingthereasoningprocessasatree,enabling
simultaneousexplorationofmultiplereasoningpaths. Startingfromaninitialstates =[q],whereq
0
istheinput,ToTincrementallyexpandseachstatebygeneratingmultiplecandidatethoughts:
|     | z(j) ∼p (z | |s ), | j =1,...,k |     | (1) |
| --- | ---------- | ----- | ---------- | --- | --- |
|     | i+1 θ      | i+1 i |            |     |     |
Eachcandidatethoughtrepresentsanodeinthetree,formingnewstates. Thesestatesareevaluated
by a heuristic scoring function V(p θ ,s), guiding the selection and pruning of branches. Search
strategies,suchasbreadth-firstsearch(BFS),systematicallyexplorethistree:
(cid:88)
|     | S =argmax |                | V(p ,s) |     | (2) |
| --- | --------- | -------------- | ------- | --- | --- |
|     | t         | S′⊆Sˆ t,|S′|=b | θ       |     |     |
s∈S′
whereSˆ
t denotescandidatestatesatstept,andblimitsthebreadth. Weimplementtwoversionsof
| heuristicfunctionsV toselectthetoptstates: |     |     |     |     |     |
| ------------------------------------------ | --- | --- | --- | --- | --- |
1. Selection: TheLLMdirectlychoosesthetoptstatestoproceed,discardingtheothers.
2. Score: Thestatesarerankedbyaheuristicvotingmechanism: V(p ,S)(s) = P[s = s∗]
θ
wheretheLLMispromptedtoestimateprobabilityofthecurrentstatesolvingthegiven
inputquestion.
Thisstructuredsearchandpruningstrategyallowsthemodeltoevaluatemultiplecandidatereasoning
paths,enablingmoredeliberateandinterpretablereasoning.
Graph-of-Thought(GoT) GoTextendsToTbyorganizingreasoningintoadirectedgraphstructure
G = (V,E),whereeachnoderepresentsathoughtandedgesreflectdependencies. Startingfrom
initialthought,newthoughtsaregeneratedsimilarlytoToTandaddedtothegraph.Eachnewthought
isconnectedtoitsparent,andadditionalreasoningchainscanbeformedthroughmergingoperations:
|     | z   | =A(z(a),z(b)) |     |     | (3) |
| --- | --- | ------------- | --- | --- | --- |
i+1 i i
4

whereAdenotesamergeoperationthatintegratestwothoughtchainsintoasinglecoherentreasoning
step.Themergedthoughtisaddedasanewnodewithedgesfrombothparents.Inourimplementation,
thoughtsareevaluatedusingeitherSelection-orScore-basedstrategyasinToT.Mergedthoughts
inheritinformationfrombothparentsandcanenhancerobustness. Ateachdepth,afixednumber
of thoughts are retained using breadth-first traversal and evaluated for progression. The graph-
basedorganizationcapturesdependenciesandmergesinformationfrommultiplereasoningchains,
supportingdynamicrefinementandstructuredexplorationofthereasoningspace.
4.2 LLM+KGInteractionMethods
WeimplementmethodstoconnectreasoningstrategieswithKGs. TheLLMinteractswiththeKGat
everystep. Thisretrievesnewinformationandconditionsthemodelforsubsequentsteps. Wepresent
2methodstoachievethisinteraction,bothillustratedinAppendixB.
4.2.1 Agent
Thisapproachcreatesanagentthatinteractswiththegraph, followingthemethodologyinitially
described in ReACT [Yao et al., 2022]. After generating a thought, the LLM selects from a set
ofactionsbasedonthegiventhought. Eachstepinthereasoningchainconsistsofaninterleaved
sequence: thought→action→retrieveddata. Thismethodimplementsfouractionsasdescribed
inGraphCoT[Jinetal.,2024]: (a)RetrieveNode(Text): Identifiestherelatednodeinthegraph
using semantic search, (b) NodeFeature(NodeID, FeatureName): Retrieves textual information
foraspecificnodefromthegraph,(c)NeighborCheck(NodeID,EdgeType): Retrievesneighbors’
informationforaspecificnode,(d)NodeDegree(NodeID,EdgeType): Returnsthedegree(#neigh-
bors)foragivennodeandedgetype. Theseactionscollectivelyenabletheagenttonavigateand
extractmeaningfulinformationfromthegraph,enhancingthereasoningcapabilitiesoftheLLMby
groundingitsthoughtsinstructured,retrievabledata.
4.2.2 AutomaticGraphExploration
Thismethodincrementallysearchesthegraphbyinterleavinglanguagegenerationwithstructured
retrieval. Ateachstep,theLLMgeneratesanew"thought"basedonpreviousthoughtsandretrieved
triples. EntitiesmentionedinthegeneratedtextareautomaticallyextractedusingLLMpromptsand
serveasanchorsforfurthergraphexploration.
Graphexplorationproceedsthroughamulti-step
Search+Prunepipeline,inspiredbytheprocess
describedinSunetal.[2024]. Foreachunvis-
itedentity,thesystemfirstretrievesandprunes
relationtypesusingLLMguidance. Then,for
eachselectedrelation,neighboringentitiesare
discoveredandfilteredusingasecondroundof
pruning. Themodelselectsonlythemostrele-
vantneighborsbasedontheircontextualfitwith
Figure3:AutomaticGraphExploration.Itextracts
thequestionandpreviousreasoningsteps. This
entitiesfromtext(query/thought),thenselectrel-
hierarchicalpruning–firstonrelations,thenon
evantrelationsandneighborswiththeLLM.The
entities–ensuresthemethodremainscomputa-
resultingentity-relation-entitycombinationsform
tionallytractablewhilepreservinginterpretabil-
triplestoexpandthereasoningchain.
ity. Theoveralltraversalfollowsabreadth-first
search(BFS)pattern,withpruningdecisionsat
eachleveldirectedbyLLM.ThisprocessisshowninFigure3. Thisiterativereasoningandretrieval
process allows the model to condition future steps on progressively relevant subgraphs, shaping
the reasoning trajectory. Unlike agentic methods that rely on predefined actions, the automatic
approachoperatesinthegraphspaceguidedbythenaturallanguage,providingmorefreedominthe
generation. Themechanismisdesignedtomaximizeinformationgainateachstepwhileavoiding
graphovergrowth. MoredetailsareprovidedinAlgorithm1.
5

5 Experiments
Benchmark WeusetheGRBenchdatasettoevaluateourmethods. Thisdatasetisspecifically
designedtoevaluatehoweffectivelyLLMscanperformstepwisereasoningoverdomain-specific
graphs. Itincludesseveralgraphsspanningvariousgeneraldomains. Forourevaluation,weselected
7graphsacrossmultipledomains,excludingthosewithexcessivelyhighRAMrequirementsthat
exceedouravailableresources. ComprehensivegraphstatisticsareprovidedinAppendixA.
Baselines Theproposedmethods,AgentandAutomaticGraphExploration,appliedtoCoT,ToT,
andGoT,arecomparedagainstthefollowingbaselinemethods: (1)Zero-Shot: Directlyquerying
themodeltoanswerthequestionwithoutadditionalcontext. (2)TextRAGGaoetal.[2023]: Text-
retrievalmethodthatusestextrepresentationofnodesasinputforquery,withretrieveddataserving
ascontextforthemodel. (3)GraphRAG:Includesnodeneighbors(1-hop)foradditionalcontext
beyondTextRAG.(4)GraphCoT(Agent): ImplementsGraphCoTasanagentforCoTreasoning,
utilizingtheactionsdescribedinSection4.2. Thesebaselinesallowustomeasureimpactofstepwise,
knowledge-groundedreasoningversussimpleretrieval-augmentedorzero-shotapproaches.
Experimentalmethods WeimplementthemethodsdescribedinSection4,extending(1)Agent
and(2)AutomaticGraphExplorationwithvariousreasoningstrategiesduringinference: (1)CoT,
(2)ToT,and(3)GoT.ForToTandGoT,weevaluatetheimpactofstepwisedecision-makingusing
StateEvaluationmethods: (1)Selectionand(2)Score. IntheresultspresentedinTable1,weset
n=10stepsforallmethods. ToTandGoTuseabranchingfactorandSelectionofk =t=3. Our
experimentsfocusontheeffectofstructuredreasoninginterventionsonperformanceandstepwise
refinementofanswers. Weuseonlyopen-accessLlama3.1(Instruct)Dubeyetal.[2024]asthe
backendmodels,whichenhancesreproducibilityandallowsforunlimitedfreecalls. Specifically,we
employthe8B,70B,and405Bversions,usingtheFP8variantforthe405Bmodel.
Evaluation Weuserule-basedandmodel-basedmetricstoevaluatethemodels,followingGRBench
paperJinetal.[2024]. Fortherule-basedmetric,weuseRouge-L(R-L)[Lin,2004],whichmeasures
thelongestsequenceofwordsappearinginsameorderinbothgeneratedtextandgroundtruthanswer.
Formodel-basedmetric,wepromptGPT-4otoassessifthemodel’soutputmatchesgroundtruth
answer. GPT4ScoreispercentageofanswersthatGPT-4oidentifiesascorrect. Theseevaluation
methodscapturenotonlyfinalansweraccuracybutalsothefidelityofreasoningsteps,reflectingthe
effectivenessofourinterventionsinguidingLLMreasoningoverstructuredknowledge.
ImplementationDetails TheexperimentsarerunonNVIDIATITANRTXorNVIDIAA100
using Python 3.8. The models are deployed with vLLM Kwon et al. [2023], a memory-efficient
libraryforLLMinferenceandserving. Forthebaseline,Mpnet-v2isusedastheretriever,andFAISS
Johnsonetal.[2019]isemployedforindexing.
6 Results
The main results from both the baselines and experimental methods, evaluated using R-L, are
presentedinTable1. Forbrevity,additionalresultsusingGPT4ScorecanbefoundinAppendixD.
Together,thesefindingsallowustocomparedifferentformsofreasoninginterventions,agenticaction
selection,automaticgraphexploration,andstructuredmulti-pathsearch,ontheirabilitytoguide
LLMstowardaccurateanswers. Wehighlightthreekeyinsightsfromthefindings: (1)Theagentic
methodgenerallyoutperformedautomaticgraphexploration,indicatingthattargetedinterventionson
knowledgegraphtraversalenhanceansweraccuracy. (2)TheToTstrategydemonstratedsuperior
performancebyeffectivelyexploringmultiplereasoningpaths,showcasingthebenefitsofinference-
timeinterventionsthatdiversifyreasoningtrajectories. (3)AlthoughGoTstrategyshowedpotential,
itdidnotsignificantlyoutperformToT,suggestingthatmergingdivergentreasoningpathsremainsa
challenginginterventiondesignproblem. Theseresultsshowtheimportanceofreasoningstrategies
inenablingLLMstonavigatemultiplepathsinthegraph,whilealsoillustratingthelimitsofcurrent
interventiontechniques.
6

Method Model Healthcare Goodreads Biology Chemistry MaterialsScience Medicine Physics
|      | Llama3.18B-Ins   | 7.32 6.18  | 10.68 11.69 | 8.95 8.77   | 11.52 |
| ---- | ---------------- | ---------- | ----------- | ----------- | ----- |
| Base | Llama3.170B-Ins  | 9.74 9.79  | 11.49 12.58 | 10.40 12.21 | 12.61 |
|      | Llama3.1405B-Ins | 8.66 12.49 | 10.52 13.51 | 11.73 11.82 | 11.63 |
senilesaB
|     | Llama3.18B-Ins | 8.24 14.69 | 12.43 11.42 | 9.46 10.75 | 11.29 |
| --- | -------------- | ---------- | ----------- | ---------- | ----- |
Text-RAG Llama3.170B-Ins 10.32 18.81 11.87 16.35 12.25 12.77 12.54
|     | Llama3.1405B-Ins | 11.61 16.23 | 16.11 13.82 | 14.23 15.16 | 16.32 |
| --- | ---------------- | ----------- | ----------- | ----------- | ----- |
|     | Llama3.18B-Ins   | 12.94 22.30 | 30.72 34.46 | 30.20 25.81 | 33.49 |
Graph-RAG Llama3.170B-Ins 17.95 25.36 38.88 40.90 41.09 31.43 39.75
|     | Llama3.1405B-Ins | 16.12 23.13 | 37.57 42.58 | 37.74 33.34 | 40.98 |
| --- | ---------------- | ----------- | ----------- | ----------- | ----- |
|     | Llama3.18B-Ins   | 16.83 30.91 | 20.15 18.43 | 26.29 14.95 | 21.41 |
Agent Llama3.170B-Ins 33.48 40.98 50.00 51.53 49.6 48.27 44.35
hparG ToC Llama3.1405B-Ins 28.41 36.56 41.35 48.36 47.81 42.54 35.24
Graph Llama3.18B-Ins 25.58 32.34 36.65 35.33 31.06 31.05 35.96
|     | Llama3.170B-Ins | 29.41 29.60 | 44.63 49.49 | 39.23 38.87 | 45.52 |
| --- | --------------- | ----------- | ----------- | ----------- | ----- |
Explore
|     | Llama3.1405B-Ins      | 28.45 43.06 | 36.93 38.71 | 47.49 55.66 | 32.73 |
| --- | --------------------- | ----------- | ----------- | ----------- | ----- |
|     | Llama3.18B-Ins        | 28.91 52.25 | 43.81 44.18 | 43.49 36.07 | 39.56 |
|     | Score Llama3.170B-Ins | 38.51 51.58 | 64.44 61.13 | 55.19 63.00 | 55.33 |
|     | Llama3.1405B-Ins      | 47.51 50.73 | 70.34 64.9  | 49.02 65.40 | 44.63 |
Agent
|     | Llama3.18B-Ins         | 28.67 50.59 | 42.33 37.07 | 40.81 33.17 | 36.50 |
| --- | ---------------------- | ----------- | ----------- | ----------- | ----- |
|     | Select Llama3.170B-Ins | 40.26 52.59 | 64.53 66.84 | 61.42 61.21 | 55.89 |
hparG Llama3.1405B-Ins 46.90 51.68 70.27 67.95 63.74 64.23 59.56
ToT
|     | Llama3.18B-Ins        | 24.49 36.80 | 35.81 36.41 | 34.28 34.49 | 37.69 |
| --- | --------------------- | ----------- | ----------- | ----------- | ----- |
|     | Score Llama3.170B-Ins | 32.79 38.19 | 53.83 58.25 | 48.55 52.18 | 48.07 |
Graph Llama3.1405B-Ins 33.90 42.68 46.87 57.43 50.46 55.56 48.73
Explore Llama3.18B-Ins 25.04 37.8 36.34 38.5 32.44 33.31 34.85
|     | Select Llama3.170B-Ins | 33.40 39.13 | 54.78 58.53 | 47.19 51.13 | 47.51 |
| --- | ---------------------- | ----------- | ----------- | ----------- | ----- |
|     | Llama3.1405B-Ins       | 33.82 43.63 | 44.47 59.06 | 48.52 55.62 | 46.07 |
Table1: Rouge-L(R-L)performanceresultsonGRBench,comparingstandardLLMs,Text-RAG,
Graph-RAG,Graph-CoT,andGraph-ToT.ExperimentsaredescribedinSection5,usingLLama3.1-
Instructbackbonemodelswithsizes8B,70B,and405B-FP8.
Agent vs Graph Search In our experimental results, the agentic method outperformed graph
explorationapproachacrossmostdatasetsandreasoningstrategies. Theagent-basedmethod,which
involves LLM selecting specific actions to interact with KG, consistently improves performance
as the number of reasoning steps increases, as shown in Section 7. This highlights that explicit,
model-driveninterventionsaremoreeffectivethanpassiveexpansionstrategies, astheypromote
iterativerefinementandselectivefocus. Whilegraphexplorationcanquicklyprovidebroadcoverage,
theagenticmethod’stargeted,stepwiseinteractionsyieldmoreaccurateandcomprehensiveanswers
overlongersequencesofreasoning.
TreeofThought(ToT) TheToTreasoningstrategyshowedsuperiorperformanceacrossitsvarious
interaction methods and state evaluators, as summarized in Table 1. ToT achieved performance
improvementsof54.74%inagentperformanceand11.74%inexplorationmodecomparedtothe
CoT baseline. However, this improvement comes with the trade-off of increased inference time,
highlightingthecostofinference-timereasoninginterventions. ThesuccessofToTillustrateshow
branchinginterventionsthatexploremultiplecandidatepathscansubstantiallyenhancereasoning
accuracy, especially when coupled with evaluators that prune unpromising trajectories. We also
comparedthetwoStateEvaluationmethods(SelectionandScore),findingcomplementarybenefits
dependingondatasetandscale.
| GraphofThought(GoT) |             | TheresultsforGoTstrategy |        |                      |         |
| ------------------- | ----------- | ------------------------ | ------ | -------------------- | ------- |
|                     |             |                          | Method | Model Healthcare     | Biology |
| are summarized      | in Table 2. | Due to the additional    | com-   |                      |         |
|                     |             |                          | erocS  | Llama3.18B-Ins 29.11 | 33.25   |
putational cost, we report results for two datasets only. Llama3.170B-Ins 30.88 56.64
GoTdidnotoutperformToT.Ourinitialhypothesiswas tnegA Llama3.1405B-Ins 43.53 48.1
|     |     |     | tceleS | Llama3.18B-Ins 29.05 | 40.37 |
| --- | --- | --- | ------ | -------------------- | ----- |
thatLLMscouldintegratedivergentresultsfrommultiple Llama3.170B-Ins 40.74 65.59
branches, butinpracticethemodelsstruggledtomerge Llama3.1405B-Ins 47.63 71.49
|                   |                                        |     |                    | Llama3.18B-Ins 24.96  | 21.72 |
| ----------------- | -------------------------------------- | --- | ------------------ | --------------------- | ----- |
| theseeffectively. | Specifically,inthegraphexplorationset- |     | erolpxEhparG erocS |                       |       |
|                   |                                        |     |                    | Llama3.170B-Ins 31.24 | 50.70 |
ting,modelsoftenfailedtocombinedifferenttriplesfound
|     |     |     |     | Llama3.1405B-Ins 35.00 | 39.10 |
| --- | --- | --- | --- | ---------------------- | ----- |
in separate branches. This reveals a current limitation tceleS Llama3.18B-Ins 25.06 21.84
|     |     |     |     | Llama3.170B-Ins 36.95 | 52.32 |
| --- | --- | --- | --- | --------------------- | ----- |
of reasoning interventions based on aggregation: while Llama3.1405B-Ins 33.74 54.64
branchinghelpsdiscoverdiversefacts,robustmechanisms
forsynthesisandreconciliationarestillunderdeveloped. Table 2: Graph-GoT results on GR-
| This finding | opens a direction | for future research | into BenchusingRouge-L |     |     |
| ------------ | ----------------- | ------------------- | ---------------------- | --- | --- |
moreadvancedinterventionstrategiesformergingpartial
reasoningoutcomes.
7

Figure 4: Effect of the number of steps in the
Figure 5: Effect of the Search depth in Graph
LLM-KG Interaction Methods. The Agent re-
Explorationinteractionmethodforafixedsteps
quiresmorestepstoobtaintheperformanceof
number. Themethodcanachieverelativelygood
theGraphExploration,whiletheGraphExplo-
performancewiththeanchorentitiesextracted
rationonlyneedstheanchorentitiestoperform
fromthequestion.
thesearchwithinthegraph.
7 Analysis&Ablationstudies
Inthissection,wewanttobetterunderstandthenuancesofourmethodsforLLMandKGgrounding.
WeconductananalysisontheAcademicdatasetsfromthebenchmark,astheyallcontainthesame
numberofsamplesandfeaturequestionsgeneratedfromsimilartemplatestoensureacontrolled
comparison.
Howdoesthenumberofstepsaffecttheresults? WeobserveinFigure4theeffectofvaryingthe
numberofstepsintheKGinteractionmethods(Agent,Explore)acrossallacademicdatasets. The
plotsindicatethatgraphexplorationperformsbetterwithfewersteps,asitautomaticallytraverses
thegraphfortheidentifiedanchorentities. Conversely,theagenticmethodsimproveasthenumber
ofstepsincreases,eventuallyachievingbetterperformance. Thisvalidatesourframework’sdesign
choicetosupportbothexplorationandagenticstrategies,eachexcelsincomplementaryregimes.
WhatistheeffectofSearchDepthinAutomaticGraphExploration? Weobservetheeffect
ofsearchdepthinFigure5,whichpresentsperformanceresultsacrossvariousdepths,withfixed
stepsizeofone. Theresultsdemonstratethattheperformanceofdepth-firstsearchplateausatdepth
of3,highlightingtherelevanceofsearchexplorationwithrespecttothegivenquery. Beyondthis
point,deepertraversalyieldsnosignificantgains,likelyduetodiminishingrelevanceofdistantnodes.
Thisshowswhyshallow,targetedexplorationissufficientinourframework,keepingsearchefficient
withoutsacrificingaccuracy.
Whatistheeffectoftreewidthinthereasoningstrategy(ToT)? Basedonexperimentalresults
acrossallacademicdatasets,weobserveperformancevariationsamongdifferentmethods. Togain
Figure6: ImpactoftreewidthonAgenticToT
Figure 7: Influence of the State Evaluators in
performance. Itshowsageneraltrendofperfor-
ToT. The Select method obtains better results
manceimprovementwithincreasingtreewidth.
overScoremethod.
8

furtherinsight,weobserveinFigure6theeffectoftreewidthonresults. Wenoticeaslightupward
trendinperformanceasthetreewidthincreases,althoughthedifferenceismorepronouncedbetween
CoTandToTitself,goingfromonebranchtotwo. Theaddedcomputationaltimeandresources
likelycontributetothisperformanceenhancement.
Whatistheinfluenceofthestateevaluator? WeobserveinFigure7theimpactofstateevaluators,
specificallyScoreandSelect,withintheToTframework. Theanalysisindicatesthat,whilethere
isnosignificantdifferencebetweenthetwomethods,theSelectevaluatorgenerallyyieldsslightly
betterresults. ThistrendisespeciallyevidentinthecontextoftheAgent’sperformance,thoughthe
advantageislesspronouncedinautomaticgraphexploration.
Howareerrorsdifferentforeachstrategy?
Tounderstandfailurepatterns,wedefinethree
errortypes: (1)Reachedlimit—thereasoning
hitthesteplimit;(2)Answerfoundbutnotre-
turned—thecorrectanswerappearedbutwas
not output; (3) Wrong reasoning step — the
modelfollowedanillogicalstep. UsingGPT-4o,
we labeled a larger set of answers and traces. (a)CoT (b)ToT (c)GoT
WeobserveinFigure8thatToTandGoTshow
more“answerfoundbutnotreturned”casesthan
CoT,suggestingbetterretrievalbutoccasional Figure8: Errordistributionacrossstrategies. ToT
failuresinsynthesis. Thiscomeswithaslight and GoT reduce unanswered cases but increase
riseinlogicalerrors,likelyduetothecomplex- logicalerrorsduetomorecomplexreasoning.
ityofmultiplereasoningpaths.
8 Limitations
Inthiswork,wedemonstratehowLLMscanbeusedtoexploreagraphwhileconditioningthenext
steps based on the graph’s results. We show that the two approaches presented achieve superior
resultsingraphexploration. IntegratingKGswithLLMscanprovidecomplexrelationalknowledge
forLLMstoleverage. However,theoveralleffectivenessdependsheavilyonboththecoverageand
qualityoftheunderlyinggraph,aswellasthecapabilitiesofthelanguagemodel.
Extendinginference-timereasoningmethodsforLLMsissignificantlyconstrainedbycomputational
resourcesandthetimeavailabletotheuser. Weanalyzethecomputationalcomplexityofthemethods
inAppendixE,whereweshowtheexponentialgrowthofToTandGoTduetoitsbranchingstructure.
GoTfurthercompoundsthisbyallowingmergesbetweenreasoningpaths,whichincreasesthetotal
numberofevaluations. Additionally,loadinglargegraphsintomemoryintroducessubstantialRAM
overhead,limitingapplicabilitytoresource-richenvironments.
WhileLLMsconditionedonexternalknowledgecangenerateoutputsbasedonaccessedcontent,
theirgeneratedoutputisnotstrictlylimitedtothatinformation. Thus,theymaystillhallucinate. Our
frameworkhelpsmitigatethisriskbygroundingreasoninginexplicitgraphstructure,butdoesnot
eliminateit.
9 Conclusion
WepresentaframeworkforgroundingLLMreasoninginKGsbyintegratingeachstepwithstructured
graphretrieval. BycombiningstrategieslikeCoT,ToT,andGoTwithadaptivegraphsearch,our
method achieves state-of-the-art performance on GRBench. Beyond performance, we find that
explicitlylinkingreasoningstepstographstructureoffersamoreinterpretableviewofhowLLMs
navigate knowledge. The approach enables inference-time reasoning, offering flexibility across
domains,andsuggestsapathtowardreasoninginterventionsthatarebothsystematicandtransparent.
Future work includes extending this framework to larger and more heterogeneous graphs, and
exploringhowstructuredretrievalcanguidereasoningindomainswhereaccuracyandverifiability
arecritical.
9

Disclaimers This[paper/presentation]waspreparedforinformationalpurposes[“inpart”ifthe
workiscollaborativewithexternalpartners]bytheArtificialIntelligenceResearchgroupofJPMor-
ganChaseanditsaffiliates("JPMorgan”)andisnotaproductoftheResearchDepartmentofJP
Morgan. JPMorganmakesnorepresentationandwarrantywhatsoeveranddisclaimsallliability,for
thecompleteness,accuracyorreliabilityoftheinformationcontainedherein. Thisdocumentisnot
intendedasinvestmentresearchorinvestmentadvice,orarecommendation,offerorsolicitationfor
thepurchaseorsaleofanysecurity,financialinstrument,financialproductorservice,ortobeused
inanywayforevaluatingthemeritsofparticipatinginanytransaction,andshallnotconstitutea
solicitationunderanyjurisdictionortoanyperson,ifsuchsolicitationundersuchjurisdictionorto
suchpersonwouldbeunlawful.
©2025JPMorganChase. Allrightsreserved
References
Ziwei Chai, Tianjie Zhang, Liang Wu, Kaiqiao Han, Xiaohai Hu, Xuanwen Huang, and Yang
Yang. Graphllm: Boosting graph reasoning ability of large language model. ArXiv preprint,
abs/2310.05845,2023. URLhttps://arxiv.org/abs/2310.05845.
AbhimanyuDubey,AbhinavJauhri,AbhinavPandey,AbhishekKadian,AhmadAl-Dahle,Aiesha
Letman,AkhilMathur,AlanSchelten,AmyYang,AngelaFan,etal. Thellama3herdofmodels.
ArXivpreprint,abs/2407.21783,2024. URLhttps://arxiv.org/abs/2407.21783.
BahareFatemi,JonathanHalcrow,andBryanPerozzi. Talklikeagraph: Encodinggraphsforlarge
languagemodels. InTheTwelfthInternationalConferenceonLearningRepresentations,2024.
URLhttps://openreview.net/forum?id=IuXR1CCrSi.
YunfanGao,YunXiong,XinyuGao,KangxiangJia,JinliuPan,YuxiBi,YiDai,JiaweiSun,Meng
Wang,andHaofenWang. Retrieval-augmentedgenerationforlargelanguagemodels: Asurvey.
ArXivpreprint,abs/2312.10997,2023. URLhttps://arxiv.org/abs/2312.10997.
Xiaoxin He, Yijun Tian, Yifei Sun, Nitesh Chawla, Thomas Laurent, Yann LeCun, Xavier
Bresson, and Bryan Hooi. G-retriever: Retrieval-augmented generation for textual
graph understanding and question answering. In A. Globerson, L. Mackey, D. Bel-
grave, A. Fan, U. Paquet, J. Tomczak, and C. Zhang, editors, Advances in Neural
Information Processing Systems, volume 37, pages 132876–132907. Curran Associates,
Inc., 2024. URL https://proceedings.neurips.cc/paper_files/paper/2024/file/
efaf1c9726648c8ba363a5c927440529-Paper-Conference.pdf.
BowenJin,ChulinXie,JiaweiZhang,KashobKumarRoy,YuZhang,SuhangWang,YuMeng,and
JiaweiHan. Graphchain-of-thought: Augmentinglargelanguagemodelsbyreasoningongraphs.
ArXivpreprint,abs/2404.07103,2024. URLhttps://arxiv.org/abs/2404.07103.
JeffJohnson,MatthijsDouze,andHervéJégou. Billion-scalesimilaritysearchwithGPUs. IEEE
TransactionsonBigData,7(3):535–547,2019.
Omar Khattab, Keshav Santhanam, Xiang Lisa Li, David Hall, Percy Liang, Christopher Potts,
andMateiZaharia. Demonstrate-search-predict: Composingretrievalandlanguagemodelsfor
knowledge-intensivenlp. ArXivpreprint,abs/2212.14024,2022. URLhttps://arxiv.org/
abs/2212.14024.
JihoKim,YeonsuKwon,YohanJo,andEdwardChoi. KG-GPT:Ageneralframeworkforreasoning
onknowledgegraphsusinglargelanguagemodels. InHoudaBouamor,JuanPino,andKalikaBali,
editors,FindingsoftheAssociationforComputationalLinguistics: EMNLP2023,pages9410–
9421,Singapore,December2023.AssociationforComputationalLinguistics. doi: 10.18653/v1/
2023.findings-emnlp.631. URLhttps://aclanthology.org/2023.findings-emnlp.631/.
MiyoungKo,SueHyunPark,JoonsukPark,andMinjoonSeo. Investigatinghowlargelanguage
modelsleverageinternalknowledgetoperformcomplexreasoning.ArXivpreprint,abs/2406.19502,
2024. URLhttps://arxiv.org/abs/2406.19502.
10

WoosukKwon,ZhuohanLi,SiyuanZhuang,YingSheng,LianminZheng,CodyHaoYu,JosephE.
Gonzalez,HaoZhang,andIonStoica. Efficientmemorymanagementforlargelanguagemodel
servingwithpagedattention. InProceedingsoftheACMSIGOPS29thSymposiumonOperating
SystemsPrinciples,2023.
Patrick S. H. Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin,
Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian
Riedel, and Douwe Kiela. Retrieval-augmented generation for knowledge-intensive NLP
tasks. In Hugo Larochelle, Marc’Aurelio Ranzato, Raia Hadsell, Maria-Florina Balcan,
and Hsuan-Tien Lin, editors, Advances in Neural Information Processing Systems 33: An-
nual Conference on Neural Information Processing Systems 2020, NeurIPS 2020, December
6-12, 2020, virtual, 2020. URL https://proceedings.neurips.cc/paper/2020/hash/
6b493230205f780e1bc26945df7481e5-Abstract.html.
FeiyangLi,PengFang,ZhanShi,ArijitKhan,FangWang,DanFeng,WeihaoWang,XinZhang,
andYongjianCui. Cot-rag: Integratingchainofthoughtandretrieval-augmentedgenerationto
enhancereasoninginlargelanguagemodels. arXivpreprintarXiv:2504.13534,2025.
Tianle Li, Xueguang Ma, Alex Zhuang, Yu Gu, Yu Su, and Wenhu Chen. Few-shot in-context
learning on knowledge base question answering. In Anna Rogers, Jordan Boyd-Graber, and
NaoakiOkazaki, editors, Proceedings ofthe 61stAnnualMeeting ofthe Associationfor Com-
putational Linguistics (Volume 1: Long Papers), pages 6966–6980, Toronto, Canada, July
2023. Association for Computational Linguistics. doi: 10.18653/v1/2023.acl-long.385. URL
https://aclanthology.org/2023.acl-long.385/.
ZhuoqunLi,XuanangChen,HaiyangYu,HongyuLin,YaojieLu,QiaoyuTang,FeiHuang,Xianpei
Han, LeSun, andYongbinLi. Structrag: Boostingknowledgeintensivereasoningofllmsvia
inference-timehybridinformationstructurization. ArXivpreprint,abs/2410.08815,2024. URL
https://arxiv.org/abs/2410.08815.
Chin-YewLin. ROUGE:Apackageforautomaticevaluationofsummaries. InTextSummariza-
tion Branches Out, pages 74–81, Barcelona, Spain, July 2004. Association for Computational
Linguistics. URLhttps://aclanthology.org/W04-1013/.
HaoranLuo,ZichenTang,ShiyaoPeng,YikaiGuo,WentaiZhang,ChenghaoMa,GuantingDong,
MeinaSong,WeiLin,etal. Chatkbqa: Agenerate-then-retrieveframeworkforknowledgebase
questionansweringwithfine-tunedlargelanguagemodels. ArXivpreprint,abs/2310.08975,2023.
URLhttps://arxiv.org/abs/2310.08975.
HaoyanLuoandLuciaSpecia. Fromunderstandingtoutilization: Asurveyonexplainabilityfor
largelanguagemodels. ArXivpreprint,abs/2401.12874,2024. URLhttps://arxiv.org/abs/
2401.12874.
Linhao Luo, Yuan-Fang Li, Reza Haf, and Shirui Pan. Reasoning on graphs: Faithful and inter-
pretablelargelanguagemodelreasoning. InTheTwelfthInternationalConferenceonLearning
Representations,2024. URLhttps://openreview.net/forum?id=ZGNWW7xZ6Q.
ElanMarkowitz,AnilRamakrishna,JwalaDhamala,NinarehMehrabi,CharithPeris,RahulGupta,
Kai-Wei Chang, and Aram Galstyan. Tree-of-traversals: A zero-shot reasoning algorithm for
augmentingblack-boxlanguagemodelswithknowledgegraphs. InLun-WeiKu,AndreMartins,
and Vivek Srikumar, editors, Proceedings of the 62nd Annual Meeting of the Association for
ComputationalLinguistics(Volume1: LongPapers),pages12302–12319,Bangkok,Thailand,
August2024.AssociationforComputationalLinguistics. doi: 10.18653/v1/2024.acl-long.665.
URLhttps://aclanthology.org/2024.acl-long.665/.
CostasMavromatisandGeorgeKarypis. Gnn-rag: Graphneuralretrievalforlargelanguagemodel
reasoning.ArXivpreprint,abs/2405.20139,2024.URLhttps://arxiv.org/abs/2405.20139.
FedorMoiseev, ZheDong,EnriqueAlfonseca,andMartinJaggi. SKILL:Structuredknowledge
infusionforlargelanguagemodels. InProceedingsofthe2022ConferenceoftheNorthAmerican
ChapteroftheAssociationforComputationalLinguistics: HumanLanguageTechnologies,pages
1581–1588, Seattle, United States, 2022. Association for Computational Linguistics. doi: 10.
18653/v1/2022.naacl-main.113. URLhttps://aclanthology.org/2022.naacl-main.113.
11

BociPeng,YunZhu,YongchaoLiu,XiaoheBo,HaizhouShi,ChuntaoHong,YanZhang,andSiliang
Tang. Graphretrieval-augmentedgeneration: Asurvey. ArXivpreprint,abs/2408.08921,2024.
URLhttps://arxiv.org/abs/2408.08921.
NitarshanRajkumar,RaymondLi,andDzmitryBahdanau. Evaluatingthetext-to-sqlcapabilitiesof
largelanguagemodels. ArXivpreprint,abs/2204.00498,2022. URLhttps://arxiv.org/abs/
2204.00498.
JiashuoSun,ChengjinXu,LumingyuanTang,SaizhuoWang,ChenLin,YeyunGong,LionelNi,
Heung-YeungShum,andJianGuo. Think-on-graph: Deepandresponsiblereasoningoflarge
language model on knowledge graph. In The Twelfth International Conference on Learning
Representations,2024. URLhttps://openreview.net/forum?id=nnVO1PvbTv.
SMTonmoy,SMZaman,VinijaJain,AnkuRani,VipulaRawte,AmanChadha,andAmitavaDas.
Acomprehensivesurveyofhallucinationmitigationtechniquesinlargelanguagemodels. ArXiv
preprint,abs/2401.01313,2024. URLhttps://arxiv.org/abs/2401.01313.
PabloVillalobos,AnsonHo,JaimeSevilla,TamayBesiroglu,LennartHeim,andMariusHobbhahn.
Willwerunoutofdata? limitsofllmscalingbasedonhuman-generateddata. ArXivpreprint,
abs/2211.04325,2022. URLhttps://arxiv.org/abs/2211.04325.
XinyiWang,AlfonsoAmayuelas,KexunZhang,LiangmingPan,WenhuChen,andWilliamYang
Wang. Understandingreasoningabilityoflanguagemodelsfromtheperspectiveofreasoning
paths aggregation. In Forty-first International Conference on Machine Learning, 2024. URL
https://openreview.net/forum?id=dZsEOFUDew.
YilinWen,ZifengWang,andJimengSun. MindMap: Knowledgegraphpromptingsparksgraph
of thoughts in large language models. In Lun-Wei Ku, Andre Martins, and Vivek Srikumar,
editors,Proceedingsofthe62ndAnnualMeetingoftheAssociationforComputationalLinguistics
(Volume1: LongPapers),pages10370–10388,Bangkok,Thailand,August2024.Associationfor
ComputationalLinguistics. doi: 10.18653/v1/2024.acl-long.558. URLhttps://aclanthology.
org/2024.acl-long.558/.
ShunyuYao,JeffreyZhao,DianYu,NanDu,IzhakShafran,KarthikNarasimhan,andYuanCao.
React: Synergizingreasoningandactinginlanguagemodels. CoRR,abs/2210.03629,2022. URL
https://doi.org/10.48550/arXiv.2210.03629.
DonghanYu,ShengZhang,PatrickNg,HenghuiZhu,AlexanderHanboLi,JunWang,YiqunHu,
William Wang, Zhiguo Wang, and Bing Xiang. Decaf: Joint decoding of answers and logical
formsforquestionansweringoverknowledgebases. ArXivpreprint,abs/2210.00063,2022. URL
https://arxiv.org/abs/2210.00063.
DannaZheng,MirellaLapata,andJeffZPan. Largelanguagemodelsasreliableknowledgebases?
ArXivpreprint,abs/2407.13578,2024. URLhttps://arxiv.org/abs/2407.13578.
AlexZhuang,GeZhang,TianyuZheng,XinrunDu,JunjieWang,WeimingRen,StephenWHuang,
JieFu,XiangYue,andWenhuChen. Structlm: Towardsbuildinggeneralistmodelsforstructured
knowledgegrounding. ArXivpreprint,abs/2402.16671,2024. URLhttps://arxiv.org/abs/
2402.16671.
Yuchen Zhuang, Yue Yu, Kuan Wang, Haotian Sun, and Chao Zhang. Toolqa: a dataset for llm
questionansweringwithexternaltools. InProceedingsofthe37thInternationalConferenceon
NeuralInformationProcessingSystems,NIPS’23,2023.
A GRBenchStatistics
DetailedstatisticsofthegraphsinGRBenchJinetal.[2024]areshowninTable3.AcademicGraphs
contain3typesofnodes: paper,author,venue. LiteratureGraphscontain4typesofnodes: book,
author,publisherandseries. HealthcareGraphcontains11typesofnodes: anatomy,biological
process,cellularcomponent,compound,disease,gene,molecularfunction,pathway,pharmacologic
class,sideeffect,andsymptom. Questionsarecreatedaccordingtomultipletemplateslabeledas
easy,medium,andhard,dependingonthenumberofnodesrequiredtogivetheanswer.
12

|            |                                               | GraphStatistics |            | Data       |
| ---------- | --------------------------------------------- | --------------- | ---------- | ---------- |
| Domain     | Topic                                         |                 |            |            |
|            |                                               | #Nodes #Edges   | #Templates | #Questions |
|            | Biology                                       | ∼4M ∼39M        | 14         | 140        |
|            | Chemistry                                     | ∼4M ∼30M        | 14         | 140        |
| Academic   | MaterialScience                               | ∼3M ∼22M        | 14         | 140        |
|            | Medicine                                      | ∼6M ∼30M        | 14         | 140        |
|            | Physics                                       | ∼2M ∼33M        | 14         | 140        |
| Literature | Goodreads                                     | ∼3M ∼22M        | 24         | 240        |
| Healthcare | Disease                                       | ∼47K ∼4M        | 27         | 270        |
| SUM        | -                                             | - -             | 121        | 1210       |
| Table3:    | DetailedstatisticsoftheGRBenchJinetal.[2024]. |                 |            |            |
B LLM<–>KGInteractionPipelines
DescriptionofthetwoLLM+KGInteractionPipelinesintheirCoTform:
1. Agent–Figure9ApipelinewheretheLLMalternatesbetweengeneratingareasoningstep,
selecting an explicit action (e.g., retrieving a node, checking neighbors), and observing
resultsfromtheKGuntiltermination.
2. Automatic Graph Exploration – Figure 10. A pipeline where entities are automatically
extractedfromtheLLM’sgeneratedtextandusedtoguideiterativegraphtraversalwith
pruning,progressivelyexpandingthereasoningchain.
Figure9: AgentPipeline: (1)InputQuery,(2)ThoughtGeneration(3)ActionSelection,(4)Environ-
mentObservationfromtheKnowledgeGraph. Theprocessisrepeateduntilterminationactionis
generatedorlimitreached.
Figure10: AutomaticGraphExplorationPipeline: (1)InputQuery, (2)ThoughtGeneration, (3)
EntityExtraction(fromqueryorthoughtwithLLM),(4)AutomaticGraphSearchasdescribedin
Algorithm1(5)QueryLLMforanswerorcontinue
13

Algorithm1presentsthepseudocodefortheAutomaticGraphExplorationdescribedinSection4.2.2.
Algorithm1GraphExplorationAlgorithm
1: procedureGRAPHEXPLORE(LLM,seen_entities,search_depth)
2: relevant_attributes,found_triples←0
3: fordepthinsearch_depthdo
4: forentityinseen_entitiesdo
5: ifseen_entities[entity_id].visited==Truethen
6: Continue
7: else
8: seen_entities[entity]←Visited
9: endif
10: head_entity_name,entity_attributes,neighbors←Graph[entity]
11: pruned_neighbors←prune_relations(LLM,neighbors)
12: pruned_neighbors←prune_entities(LLM,pruned_neighbors)
13: found_triples←generate_triples(entity,pruned_neighbros)
14: endfor
15: seen_entities←Update(seen_entities,neighbors)
16: ifEnd?(LLM,found_triples,relevant_attributes)==Truethen
17: break
18: endif
19: endfor
20: returnfound_triples,relevant_attributes,seen_entities
21: endprocedure
C Performanceresultsinplots
Figures 11 and 12 illustrate the performance results using the Rouge-L and GPT4score metrics,
respectively,forthehealthcaregraphforallmethods. TheresultswererunontheLLama3.1Instruct
models(8B,70B,and405B-FP8)anddemonstratetheimprovedperformanceachievedthroughmore
complexreasoningandsearchstrategiesduringinference.
Figure11: PerformanceresultsusingtheRouge-LmetriconthehealthcaregraphofGRBenchJin
et al. [2024], comparing all methods with LLama 3.1 Instruct models of various sizes (8B, 70B,
405B-FP8). ExperimentaldetailsareincludedinSection5.
14

Figure12: PerformanceresultsusingtheGPT4ScoremetriconthehealthcaregraphofGRBench
Jinetal.[2024],comparingallmethodswithLLama3.1Instructmodelsofvarioussizes(8B,70B,
405B-FP8). ExperimentaldetailsareincludedinSection5.
D ResultsonGPT4Score
In this section, we present the results of the experiments described in Section 5 for all methods,
usingtheGPT4Scoremetric. Thismetriccalculatesthepercentageof"correct"answersasjudged
byGPT-4whenpresentedwithboththecorrectandthegeneratedanswer. Thetablesinthissection
presentthesamedataasinTables1and2,butevaluatedusingGPT4Score.
| Method | Model            | Healthcare Goodreads | Biology Chemistry | MaterialsScience Medicine | Physics |
| ------ | ---------------- | -------------------- | ----------------- | ------------------------- | ------- |
|        | Llama3.18B-Ins   | 11.85 13.33          | 10.71 11.43       | 7.86 7.87                 | 9.29    |
| Base   | Llama3.170B-Ins  | 12.96 19.17          | 10.00 12.14       | 11.43 11.43               | 12.86   |
|        | Llama3.1405B-Ins | 15.55 26.67          | 12.86 12.14       | 12.14 13.57               | 12.14   |
senilesaB Llama3.18B-Ins 11.85 21.67 12.86 10.00 10.00 8.57 7.86
| Text-RAG  | Llama3.170B-Ins  | 12.22 27.5  | 12.14 13.57 | 13.57 13.57 | 12.86 |
| --------- | ---------------- | ----------- | ----------- | ----------- | ----- |
|           | Llama3.1405B-Ins | 12.96 26.67 | 15.00 13.57 | 12.86 14.29 | 13.57 |
|           | Llama3.18B-Ins   | 14.81 32.50 | 29.29 29.28 | 27.86 25.71 | 29.29 |
| Graph-RAG | Llama3.170B-Ins  | 17.04 32.92 | 39.29 40.71 | 43.57 34.29 | 40.00 |
|           | Llama3.1405B-Ins | 18.15 31.67 | 37.14 42.86 | 40.00 36.43 | 41.43 |
|           | Llama3.18B-Ins   | 18.15 32.5  | 20.71 19.28 | 25.00 14.29 | 21.43 |
hparG Agent Llama3.170B-Ins 32.59 43.75 50.00 51.43 50.00 48.57 46.43
ToC Llama3.1405B-Ins 28.89 48.33 38.57 38.57 47.86 56.43 34.29
|       | Llama3.18B-Ins  | 22.22 36.67 | 35.00 30.71 | 29.29 29.29 | 32.86 |
| ----- | --------------- | ----------- | ----------- | ----------- | ----- |
| Graph | Llama3.170B-Ins | 27.78 32.92 | 45.71 49.29 | 40.00 40.00 | 44.29 |
Explore
|        | Llama3.1405B-Ins | 28.89 48.33 | 38.57 38.57 | 47.86 56.43 | 34.29 |
| ------ | ---------------- | ----------- | ----------- | ----------- | ----- |
|        | Llama3.18B-Ins   | 30.49 55.14 | 43.33 41.67 | 44.05 36.43 | 39.52 |
| Score  | Llama3.170B-Ins  | 30.49 54.48 | 65.48 62.14 | 55.95 63.57 | 56.19 |
| Agent  | Llama3.1405B-Ins | 45.55 56.53 | 71.67 65.71 | 52.62 68.81 | 44.76 |
|        | Llama3.18B-Ins   | 30.00 54.17 | 40.71 37.14 | 40.00 32.86 | 36.43 |
| Select | Llama3.170B-Ins  | 39.63 56.67 | 65.00 67.14 | 62.86 60.71 | 55.55 |
hparG
ToT Llama3.1405B-Ins 44.07 58.75 71.43 69.29 65.00 68.81 60.00
|         | Llama3.18B-Ins   | 21.48 41.10 | 32.86 31.67 | 31.43 32.14 | 35.24 |
| ------- | ---------------- | ----------- | ----------- | ----------- | ----- |
| Score   | Llama3.170B-Ins  | 24.94 40.97 | 52.38 57.86 | 49.29 54.29 | 47.86 |
| Graph   | Llama3.1405B-Ins | 30.86 48.33 | 47.86 57.14 | 50.71 56.67 | 47.14 |
| Explore | Llama3.18B-Ins   | 21.85 41.67 | 32.86 31.67 | 31.43 32.14 | 35.24 |
| Select  | Llama3.170B-Ins  | 30.37 42.08 | 54.29 57.14 | 47.86 52.14 | 46.43 |
|         | Llama3.1405B-Ins | 31.48 48.75 | 45.00 57.86 | 48.86 57.14 | 45.71 |
Table4: GPT4ScoreperformanceresultsonGRBenchJinetal.[2024],comparingstandardLLMs,
Text-RAG,Graph-RAG,Graph-CoT,andGraph-ToT.ExperimentsaredescribedinSection5,using
LLama3.1-Instructbackbonemodelswithsizes8B,70B,and405B.
15

|     | Method |                | Model | Healthcare | Biology |       |     |     |     |     |     |
| --- | ------ | -------------- | ----- | ---------- | ------- | ----- | --- | --- | --- | --- | --- |
|     |        | Llama3.18B-Ins |       |            | 29.88   | 32.86 |     |     |     |     |     |
erocS
|     |       | Llama3.170B-Ins  |     |     | 29.51 | 61.69 |     |     |     |     |     |
| --- | ----- | ---------------- | --- | --- | ----- | ----- | --- | --- | --- | --- | --- |
|     | tnegA | Llama3.1405B-Ins |     |     | 41.81 | 48.33 |     |     |     |     |     |
|     |       | Llama3.18B-Ins   |     |     | 30.00 | 40.71 |     |     |     |     |     |
tceleS
|           |              | Llama3.170B-Ins               |     |     | 39.63 | 69.83 |     |            |         |            |      |
| --------- | ------------ | ----------------------------- | --- | --- | ----- | ----- | --- | ---------- | ------- | ---------- | ---- |
|           |              | Llama3.1405B-Ins              |     |     | 44.81 | 72.86 |     |            |         |            |      |
|           | erolpxEhparG | erocS Llama3.18B-Ins          |     |     | 22.72 | 21.19 |     |            |         |            |      |
|           |              | Llama3.170B-Ins               |     |     | 24.20 | 48.57 |     |            |         |            |      |
|           |              | Llama3.1405B-Ins              |     |     | 32.22 | 41.67 |     |            |         |            |      |
|           |              | tceleS Llama3.18B-Ins         |     |     | 22.59 | 19.28 |     |            |         |            |      |
|           |              | Llama3.170B-Ins               |     |     | 32.96 | 52.86 |     |            |         |            |      |
|           |              | Llama3.1405B-Ins              |     |     | 31.48 | 57.86 |     |            |         |            |      |
| Figure13: |              | Graph-GoTresults(GPT4Score)on |     |     |       |       |     |            |         |            |      |
|           |              |                               |     |     |       |       |     | Figure 14: | Results | decomposed | into |
GRBenchwithLlama3.1Instructsizes8B,70B,
| and405B. |     |     |     |     |     |     |     | easy/medium/hard | questions | according | to  |
| -------- | --- | --- | --- | --- | --- | --- | --- | ---------------- | --------- | --------- | --- |
GPT4Score.
E ComputationalAnalysis
Method KeyParame- Approx.#LLMCalls Approx.#KGOperations Primary Growth
|     |              |     | ters |     |          |     |          |                     |     | Driver(s) |     |
| --- | ------------ | --- | ---- | --- | -------- | --- | -------- | ------------------- | --- | --------- | --- |
|     | ToC Agent    |     | n    |     | O(n)     |     |          | O(n)                |     | n(linear) |     |
|     | GraphExplore |     | n,d  |     | O(n)     |     |          | O(n·CostExplore(d)) |     | n,d       |     |
|     |              |     |      |     | (cid:16) |     | (cid:17) |                     |     |           |     |
Agent Dmax,k,t O k·tD m ax −1 SameasLLMCalls Dmax,k,t(exponen-
|     | ToT |     |     |     |     | t − 1 |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | ----- | --- | --- | --- | --- | --- |
tialinDmax)
|     |              |     |            |     | (cid:16) |              | (cid:17) | (cid:16)                      |     | (cid:17)   |     |
| --- | ------------ | --- | ---------- | --- | -------- | ------------ | -------- | ----------------------------- | --- | ---------- | --- |
|     | GraphExplore |     | Dmax,k,t,d |     | O        | k·tD m ax −1 |          | O k·tD m ax −1·CostExplore(d) |     | Dmax,k,t,d |     |
|     |              |     |            |     |          | t − 1        |          | t − 1                         |     |            |     |
ToG Agent Dmax,k,t S a m easLLMCalls D , k , t (a g g re g a -
|     |              |     |            |     | . (cid:18)  |                   |      | (cid:22) (cid:23) (cid:19) |     | m ax       |                      |
| --- | ------------ | --- | ---------- | --- | ----------- | ----------------- | ---- | -------------------------- | --- | ---------- | -------------------- |
|     |              |     |            |     | O k·tD      | m ax −1+(cid:80)D | m ax | k· t i                     |     | t io n a d | d s ex tr a c o s t) |
|     |              |     |            |     |             | t − 1             | i= 1 | 2                          |     |            |                      |
|     | GraphExplore |     | Dmax,k,t,d |     | SameasAgent |                   |      | O(LLMCalls·CostExplore(d)) |     | Dmax,k,t,d |                      |
Table5: Theoreticalcomputationalcomplexitycomparisonofreasoningmethods. Parameters: n
(reasoningsteps),D (treedepth),k(branchingfactor),t(pathsretained),d(KGsearchdepth),and
max
Cost (d)(costperKGsearch). GoTincludespairwiseaggregationofthoughtsateachdepth.
Explore
| The | computational |     | analysis |     | summarized | in  | Table | 5 high- |     |     |     |
| --- | ------------- | --- | -------- | --- | ---------- | --- | ----- | ------- | --- | --- | --- |
lightsthetrade-offsbetweenreasoningpowerandcomputa-
tionalcostwhengroundingLLMswithKnowledgeGraphs
| (KGs). |     | The Agent-based |     | methods | scale | linearly | with | the |     |     |     |
| ------ | --- | --------------- | --- | ------- | ----- | -------- | ---- | --- | --- | --- | --- |
numberofreasoningstepsortreenodes,withCoTrepresent-
| ingthelowestcostbaseline. |     |     |     |     | Incontrast,AutomaticGraph |     |     |     |     |     |     |
| ------------------------- | --- | --- | --- | --- | ------------------------- | --- | --- | --- | --- | --- | --- |
Explorationmethodsintroduceadditionaloverheadviaen-
tityextraction,multi-hoptraversaluptoafixedmax_depth,
andLLM-basedpruningateachstep.
| Among |     | reasoning | strategies, |     | ToT introduces |     | exponential |     |     |     |     |
| ----- | --- | --------- | ----------- | --- | -------------- | --- | ----------- | --- | --- | --- | --- |
growthincostwithrespecttodepthduetoitsexplorationof
| kbranchesandselectionoftcontinuationsperlevel. |     |     |     |     |     |     |     | GoT |     |     |     |
| ---------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
further amplifies this by incorporating aggregation trans- Figure 15: Comparison of computa-
formationsthatattempttomergeeverypairofthoughtsat tionalcostsacrossdifferentreasoning
|      |           |           |     |               |     |                   |     | strategies                | —   | CoT, ToT, | GoT — as a |
| ---- | --------- | --------- | --- | ------------- | --- | ----------------- | --- | ------------------------- | --- | --------- | ---------- |
| each | depth,    | leading   | to  | an additional |     | cost proportional |     | to                        |     |           |            |
|      | (cid:106) | (cid:107) |     |               |     |                   |     | functionofreasoningsteps. |     |           | GoTex-     |
(cid:80)Dmax k·ti
.
|     | i=1 | 2   |     |     |     |     |     | hibits | the highest | cost due | to merge |
| --- | --- | --- | --- | --- | --- | --- | --- | ------ | ----------- | -------- | -------- |
operationsandgraphtraversal.
| Importantly, |     | our | experiments |     | reveal | that the | higher | com- |     |     |     |
| ------------ | --- | --- | ----------- | --- | ------ | -------- | ------ | ---- | --- | --- | --- |
plexityofGoTdoesnotconsistentlytranslatetoimproved
accuracycomparedtoToT,suggestingdiminishingreturns.
Whilethemodelsize(e.g.,8B,70B,405B)influencesthe
latencyandmemoryfootprintofeachLLMcall,itdoesnotaffectthealgorithmiccomplexityclasses
shown. Hence,selectingastrategyrequiresbalancingreasoningdepthwithfeasiblecomputebudgets.
16

F PromptsArchive
Inthissection,wegatherthenecessarypromptsessentialforimplementingtheproposedmethodolo-
gies.
Agent
Agent Step: Solve a question answering task with interleaving
Thought, Interaction with Graph, Feedback from Graph steps. In
Thought step, you can think about what further information is needed,
and In Interaction step, you can get feedback from graphs with four
functions:
(1) RetrieveNode[keyword], which retrieves the related node from the
graph according to the corresponding query.
(2) NodeFeature[Node, feature], which returns the detailed attribute
information of Node regarding the given "feature" key. (3)
NodeDegree[Node, neighbor_type], which calculates the number of
"neighbor_type" neighbors of the node Node in the graph.
(4) NeighbourCheck[Node, neighbor_type], which lists the
"neighbor_type" neighbours of the node Node in the graph and returns
them.
You may take as many steps as necessary.
Here are some examples:
{examples}
Please answer by providing node main feature (e.g., names) rather
than node IDs.
Generate the next step.
Definition of the graph: {graph_definition}
Question: {question}
{scratchpad}
AutomaticGraphExploration
Search Thought: Given the previous thoughts, generate the next
thought to answer the provided question.
Your end goal is to answer the question step by step. For context,
you are also provided with some knowledge triples from a knowledge
base.
Follow the format of the examples to generate the next thought.
{examples}
Graph Definition: {graph_definition}
Question: {question}
Knowledge Triples:
{triples}
Previous thoughts:
{thoughts}
Related Entity Attributes:
{attributes}
Next Thought:
Search End?: Your are provided with the an original question, the
associated subquestion thoughts and their corresponding knowledge
graph triples (head_entity -> relation -> tail_entity). Your task
is to answer whether it’s sufficient for you to answer the original
question (Yes or No). You are provided with examples. You should
follow the same format as in the examples, writing ’Yes’ or ’No’
17

| within | brackets | at  | the beginning |     | of  | the answer. |     |
| ------ | -------- | --- | ------------- | --- | --- | ----------- | --- |
(Examples)
| Task:     | Question:   | {question} |              |     |     |     |     |
| --------- | ----------- | ---------- | ------------ | --- | --- | --- | --- |
| Thoughts: | {thoughts}  |            |              |     |     |     |     |
| Knowledge | Triples:    |            | {triples}    |     |     |     |     |
| Entity    | Attributes: |            | {attributes} |     |     |     |     |
Answer:
Entity Extraction: Given the provided text, extract the relevant
entities that may appear in a knowledge base. Return the answer at
the end with brackets relevant entities as shown in the following
examples. If there are several entities, separate them with commas.
(Examples)
| Task:    | Text:     | {text} |     |     |     |     |     |
| -------- | --------- | ------ | --- | --- | --- | --- | --- |
| Relevant | Entities: |        |     |     |     |     |     |
Prune Relations: From the given entity and relations, select only
the relevant relations to answer the question. Provide the answer at
| the end | with | bracketsanswer |     | ,   | as shown | in the following | example. |
| ------- | ---- | -------------- | --- | --- | -------- | ---------------- | -------- |
(Examples)
| Question:    | {question}  |          |         |     |     |     |     |
| ------------ | ----------- | -------- | ------- | --- | --- | --- | --- |
| Head Entity: |             | {entity} |         |     |     |     |     |
| Relations:   | {relations} |          | Answer: |     |     |     |     |
Prune entities: You are provided with a question, a head entity,
a relation and tail entity or entities from a knowledge base. Select
| the tail | entity | or  | entities | to  | answer | the question. | Return the |
| -------- | ------ | --- | -------- | --- | ------ | ------------- | ---------- |
tail entity or entities at the end with brackets relevant entity or
| entities, | as  | shown | in the | following |     | examples. |     |
| --------- | --- | ----- | ------ | --------- | --- | --------- | --- |
(Examples)
| Question:      | {question} |                 |     |     |     |     |     |
| -------------- | ---------- | --------------- | --- | --- | --- | --- | --- |
| Head Entity:   |            | {head_entity}   |     |     |     |     |     |
| Relation:      | {relation} |                 |     |     |     |     |     |
| Tail Entities: |            | {tail_entities} |     |     |     |     |     |
| Relevant       | Entities:  |                 |     |     |     |     |     |
Search Attributes: Is any of the attributes relevant to answer the
question? Return the answer at the end with brackets answer , as
| shown in | the | following | examples. |     |     |     |     |
| -------- | --- | --------- | --------- | --- | --- | --- | --- |
(Examples)
| Question:   | {question}  |              |     |     |     |     |     |
| ----------- | ----------- | ------------ | --- | --- | --- | --- | --- |
| Entity:     | {entity}    |              |     |     |     |     |     |
| Attributes: |             | {attributes} |     |     |     |     |     |
| Relevant    | Attributes: |              |     |     |     |     |     |
StateEvaluators
SelectionVote: Givenaquestion,youneedtoselectthepossiblechainofthoughtthatmay
leadtothecorrectanswerwithhigherprobablity. Youareprovidedwithseveralchoiceswith
thouhgtsandrelatedtriplesfromaknowledgebase. Decidewhichchoiceismostpromising
tocompletethetask. Analyzeeachchoiceindetail,thenconcludeinthelastline: "Thebest
choiceiss",wherestheintegeridofthechoice.
(Examples)
| Question: | {question} |     |     |     |     |     |     |
| --------- | ---------- | --- | --- | --- | --- | --- | --- |
Choices: {choices}(+attributes/triples)
Answer:
18

Score Vote: Generate a score for the given reasoning chain. The score represents
theprobabilitythatthechainwillleadtothecorrectanswer. Thechainscontaininterleaved
thoughtsandrelatedtriplesfromaknowledgebase. Somechainsmaynotbecomplete,but
youneedtojudgethestepsthatareprovided. Thescorecanbeanyfloatingnumberbetween
0and1.
(Examples)
Question: {question}
ThoughtChain: {thoughts}(+attributes/triples)
Score:
GraphofThoughts
GraphofThoughtMerge: Generatethenextthoughtforthemergedchainofthoughts. You
areprovidedwiththequestion,twochainsofthoughts,andthecorrespondingmergedchain
ofthought. Identifyinconsistenciesorerrorsfromthepreviouschainsandprovidethenext
thoughtforthemergedchain. Youshouldfollowthesameformatasintheexamples.
(Examples)
Question: {question}
Chain1: {chain_1}(+triples/attributes)
Chain2: {chain_2}(+triples/attributes)
MergedChain: {merged_chain}
NextThought:
19

G Examples
Example1: Multi-stepReasoningoverGraph Example2: DirectTripleLookup
Question: Whatanatomycanbeexpressedby Question: Whatanatomycanbeexpressedby
| geneKRT39? |     |     |     | geneKRT39? |     |
| ---------- | --- | --- | --- | ---------- | --- |
GroundTruthAnswer: head,skinofbody GroundTruthAnswer: head,skinofbody
| ModelAnswer: | head,skinofbody |     |     | ModelAnswer: | head,skinofbody |
| ------------ | --------------- | --- | --- | ------------ | --------------- |
Thought 1: The question is related to a gene Thought1: KRT39isagenethatisknowntobe
node(KRT39). Weneedtofindthisnodeinthe expressedintwoanatomicalregions.
| graph.        |                         |     |     | FoundTriples: |                           |
| ------------- | ----------------------- | --- | --- | ------------- | ------------------------- |
| Action1:      | RetrieveNode[KRT39]     |     |     |               |                           |
|               |                         |     |     | • "KRT39"     | –> Anatomy-expresses-Gene |
| Observation1: | TheIDofthenodeis390792. |     |     |               |                           |
–> head
| Thought | 2: We need | to check the | ’Anatomy- |           |                           |
| ------- | ---------- | ------------ | --------- | --------- | ------------------------- |
|         |            |              |           | • "KRT39" | –> Anatomy-expresses-Gene |
expresses-Gene’neighborsofthisgenenode.
|        |                           |     |     | –> skin              | of body       |
| ------ | ------------------------- | --- | --- | -------------------- | ------------- |
| Action | 2: NeighbourCheck[390792, |     |     |                      |               |
|        |                           |     |     | Action: Finish[head, | skin of body] |
Anatomy-expresses-Gene]
| Observation | 2:  | The                | neigh- |     |     |
| ----------- | --- | ------------------ | ------ | --- | --- |
| bors        | are | [’UBERON:0000033’, |        |     |     |
’UBERON:0002097’].
| Thought | 3: Retrieve | names of | the anatomy |     |     |
| ------- | ----------- | -------- | ----------- | --- | --- |
nodes.
| Action | 3: NodeFeature[UBERON:0000033, |     |     |     |     |
| ------ | ------------------------------ | --- | --- | --- | --- |
| name], | NodeFeature[UBERON:0002097,    |     |     |     |     |
name]
| Observation | 3:  |     | → head, |     |     |
| ----------- | --- | --- | ------- | --- | --- |
UBERON:0000033
UBERON:0002097→skinofbody.
| Thought | 4: These are | the anatomy | terms ex- |     |     |
| ------- | ------------ | ----------- | --------- | --- | --- |
pressedbythegene.
| Action4: | Finish[head, | skin | of body] |     |     |
| -------- | ------------ | ---- | -------- | --- | --- |
Table6: ComparisonoftwoLLM-generatedreasoningtracesforthesamequestionusingdifferent
strategies: multi-stepgraphtraversal(Example1)vs. directtriplelookup(Example2).
20